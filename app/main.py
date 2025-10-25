#!/usr/bin/env python3
"""
CrewAI Chat Passthrough Agent
Pure passthrough to Claude Sonnet 4 with zero funnel logic
"""

import os
import sys
import time
import json
import sqlite3
import requests
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context, send_from_directory
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import uuid

# Environment variables
API_PORT = int(os.environ.get('API_PORT', 8080))
METRICS_PORT = int(os.environ.get('METRICS_PORT', 9090))
C2_REGISTRY_URL = os.environ.get('C2_REGISTRY_URL', 'http://crewai-c2-dc1-prod-001-v1-0-0:8080')
DATA_DIR = os.environ.get('DATA_DIR', './data')
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', './output')
PIDFILE = os.environ.get('PIDFILE', '/var/run/crewai-chat-passthrough.pid')

# Prometheus metrics
chat_messages_total = Counter('crewai_chat_messages_total', 'Total chat messages', ['direction', 'user'])
chat_sessions_active = Gauge('crewai_chat_sessions_active', 'Active chat sessions')
chat_response_time = Histogram('crewai_chat_response_time_seconds', 'Chat response time')
chat_tokens_total = Counter('crewai_chat_tokens_total', 'Total tokens processed', ['type'])
llm_requests_total = Counter('crewai_chat_llm_requests_total', 'Total LLM requests', ['status'])
chat_errors_total = Counter('crewai_chat_errors_total', 'Total chat errors', ['type'])

app = Flask(__name__)

# CORS configuration
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Database setup
class ChatDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Users/Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')

            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tokens INTEGER,
                    response_time REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON messages(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id)')

            conn.commit()

    def create_session(self, user_id, metadata=None):
        """Create a new chat session"""
        session_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sessions (session_id, user_id, metadata)
                VALUES (?, ?, ?)
            ''', (session_id, user_id, json.dumps(metadata or {})))
            conn.commit()

        chat_sessions_active.inc()
        return session_id

    def save_message(self, session_id, role, content, tokens=None, response_time=None):
        """Save a message to the database"""
        message_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (message_id, session_id, role, content, tokens, response_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (message_id, session_id, role, content, tokens, response_time))

            # Update session last_active
            cursor.execute('''
                UPDATE sessions SET last_active = CURRENT_TIMESTAMP
                WHERE session_id = ?
            ''', (session_id,))

            conn.commit()

        return message_id

    def get_history(self, session_id, limit=50):
        """Get chat history for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT message_id, role, content, timestamp, tokens, response_time
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (session_id, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'message_id': row[0],
                    'role': row[1],
                    'content': row[2],
                    'timestamp': row[3],
                    'tokens': row[4],
                    'response_time': row[5]
                })

            return list(reversed(messages))

    def get_user_sessions(self, user_id):
        """Get all sessions for a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, created_at, last_active, metadata
                FROM sessions
                WHERE user_id = ?
                ORDER BY last_active DESC
            ''', (user_id,))

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    'session_id': row[0],
                    'created_at': row[1],
                    'last_active': row[2],
                    'metadata': json.loads(row[3]) if row[3] else {}
                })

            return sessions

    def get_active_session_count(self):
        """Get count of active sessions (last 1 hour)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM sessions
                WHERE last_active >= datetime('now', '-1 hour')
            ''')
            return cursor.fetchone()[0]

# Initialize database
db = ChatDatabase(os.path.join(DATA_DIR, 'chat.db'))

# Claude LLM - Pure Passthrough
class ClaudeLLM:
    """Pure passthrough to Claude API with minimal system prompt"""
    def __init__(self, api_key=None):
        # Try multiple sources for API key
        self.api_key = (api_key or
                       os.environ.get('ANTHROPIC_API_KEY') or
                       os.environ.get('CLAUDE_API_KEY'))

        # If no key found, try to read from common locations
        if not self.api_key:
            key_locations = [
                os.path.expanduser('~/.anthropic/api_key'),
                os.path.expanduser('~/.config/claude/api_key'),
                os.path.expanduser('~/.claude/api_key'),
            ]
            for loc in key_locations:
                try:
                    if os.path.exists(loc):
                        with open(loc) as f:
                            self.api_key = f.read().strip()
                            break
                except:
                    continue

        if not self.api_key:
            raise ValueError("No Anthropic API key found. Set ANTHROPIC_API_KEY or create ~/.anthropic/api_key")

        self.api_url = "https://api.anthropic.com/v1/messages"

    def generate_stream(self, prompt, session_id, conversation_history=None):
        """Generate streaming response from Claude - pure passthrough"""
        try:
            # Minimal system prompt - no data context, no instructions
            system_message = "You are Claude, a helpful AI assistant."

            # Build conversation messages from history if provided
            messages = []
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages for context
                    if msg['role'] in ['user', 'assistant']:
                        messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })

            # Add current user message
            messages.append({
                'role': 'user',
                'content': prompt
            })

            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8192,  # Large limit for passthrough
                "temperature": 1.0,   # Default temperature
                "system": system_message,
                "messages": messages,
                "stream": True
            }

            llm_requests_total.labels(status='initiated').inc()

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=60,
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': self.api_key,
                    'anthropic-version': '2023-06-01'
                },
                stream=True
            )

            if response.status_code != 200:
                llm_requests_total.labels(status='error').inc()
                error_msg = f'Claude API error: {response.status_code} - {response.text[:200]}'
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
                return

            llm_requests_total.labels(status='success').inc()

            # Parse SSE stream from Claude
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data_str = line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if data.get('type') == 'content_block_delta':
                                delta = data.get('delta', {})
                                if delta.get('type') == 'text_delta':
                                    text = delta.get('text', '')
                                    full_response += text
                                    yield f"data: {json.dumps({'token': text})}\n\n"
                                    chat_tokens_total.labels(type='generated').inc()
                        except json.JSONDecodeError:
                            continue

            # Send completion signal
            yield f"data: {json.dumps({'done': True})}\n\n"
            return full_response

        except Exception as e:
            chat_errors_total.labels(type='llm_error').inc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"


# Service Registration with C2
def register_with_c2():
    """Register this agent with C2 service registry"""
    try:
        import socket
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)

        service_data = {
            'id': 'crewai-chat-passthrough-001',
            'name': 'crewai-chat-passthrough',
            'type': 'chat',
            'address': ip_address,
            'port': API_PORT,
            'capabilities': ['chat', 'claude-passthrough', 'streaming'],
            'tags': ['production', 'chat-interface', 'passthrough'],
            'datacenter': 'dc1',
            'environment': 'prod',
            'instance_id': '001',
            'version': 'v1.0.0'
        }

        response = requests.post(
            f"{C2_REGISTRY_URL}/registry/register",
            json=service_data,
            timeout=5
        )

        if response.status_code == 200:
            print(f"Registered with C2 at {C2_REGISTRY_URL}")
            return True
        else:
            print(f"Failed to register with C2: {response.status_code}")
            return False

    except Exception as e:
        print(f"C2 registration error: {e}")
        return False

# Flask routes - Standard A2A endpoints
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'crewai-chat-passthrough'})

@app.route('/status', methods=['GET'])
def status():
    active_sessions = db.get_active_session_count()
    chat_sessions_active.set(active_sessions)

    return jsonify({
        'id': 'crewai-chat-passthrough',
        'name': 'CrewAI Chat Passthrough Agent',
        'type': 'chat',
        'capabilities': ['chat', 'claude-passthrough', 'streaming'],
        'active_sessions': active_sessions,
        'llm_model': 'claude-sonnet-4'
    })

@app.route('/config', methods=['GET'])
def get_config():
    return jsonify({
        'api_port': API_PORT,
        'metrics_port': METRICS_PORT,
        'c2_registry_url': C2_REGISTRY_URL,
        'data_dir': DATA_DIR
    })

@app.route('/config', methods=['POST'])
def update_config():
    return jsonify({'error': 'Config updates not implemented'}), 501

@app.route('/job', methods=['POST'])
def process_job():
    return jsonify({'status': 'job processing not applicable for chat agent'}), 501

@app.route('/batch', methods=['POST'])
def process_batch():
    return jsonify({'status': 'batch processing not applicable for chat agent'}), 501

# Chat endpoints
@app.route('/chat', methods=['GET'])
def chat_ui():
    """Serve chat interface"""
    return send_from_directory(os.path.dirname(__file__), 'chat.html')

@app.route('/chat/session/new', methods=['POST'])
def new_session():
    """Create a new chat session"""
    data = request.get_json() or {}
    user_id = data.get('user_id', 'anonymous')
    metadata = data.get('metadata', {})

    session_id = db.create_session(user_id, metadata)

    return jsonify({
        'session_id': session_id,
        'user_id': user_id,
        'created_at': datetime.now().isoformat()
    })

@app.route('/chat/send', methods=['POST'])
def send_message():
    """Send a message and get streaming response - pure passthrough"""
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'message required'}), 400

    session_id = data.get('session_id')
    user_id = data.get('user_id', 'anonymous')
    message = data['message']

    # Create session if not provided
    if not session_id:
        session_id = db.create_session(user_id)

    # Save user message
    db.save_message(session_id, 'user', message)
    chat_messages_total.labels(direction='incoming', user=user_id).inc()

    # Get conversation history for context
    history = db.get_history(session_id, limit=10)

    # Stream response
    def generate():
        start_time = time.time()
        full_response = ""

        # Send model indicator
        yield f"data: {json.dumps({'model': 'Claude Sonnet 4'})}\n\n"

        try:
            for chunk in llm.generate_stream(message, session_id, conversation_history=history):
                # Parse the SSE data
                if chunk.startswith('data: '):
                    data = json.loads(chunk[6:])
                    if 'token' in data:
                        full_response += data['token']
                yield chunk

            # Save assistant response
            response_time = time.time() - start_time
            chat_response_time.observe(response_time)

            if full_response:
                db.save_message(
                    session_id,
                    'assistant',
                    full_response,
                    tokens=len(full_response.split()),
                    response_time=response_time
                )
                chat_messages_total.labels(direction='outgoing', user=user_id).inc()

        except Exception as e:
            chat_errors_total.labels(type='streaming_error').inc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )

@app.route('/chat/history', methods=['GET'])
def get_history():
    """Get chat history for a session"""
    session_id = request.args.get('session_id')
    limit = int(request.args.get('limit', 50))

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    history = db.get_history(session_id, limit)
    return jsonify({'history': history, 'session_id': session_id})

@app.route('/chat/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions for a user"""
    user_id = request.args.get('user_id', 'anonymous')
    sessions = db.get_user_sessions(user_id)
    return jsonify({'sessions': sessions, 'user_id': user_id})

# Metrics endpoint
@app.route('/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    # Write PID file
    with open(PIDFILE, 'w') as f:
        f.write(str(os.getpid()))

    # Initialize LLM
    global llm
    try:
        llm = ClaudeLLM()
        print(f"✓ Claude Sonnet 4 passthrough initialized")
    except ValueError as e:
        print(f"ERROR: Could not initialize Claude: {e}")
        sys.exit(1)

    # Register with C2
    register_with_c2()

    print(f"Starting CrewAI Chat Passthrough Agent on port {API_PORT}")
    print(f"Metrics available on port {METRICS_PORT}")
    print(f"Mode: Pure passthrough to Claude Sonnet 4")

    # Start Flask
    app.run(host='0.0.0.0', port=API_PORT, threaded=True)

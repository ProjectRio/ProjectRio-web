from flask import request, jsonify
from flask import current_app as app
from sqlalchemy import desc, text
from ..models import db, OngoingGame, RioUser, UserGroupUser, UserGroup
from ..user_util import get_user
import os
import json
import time
import platform
import psutil


def _is_admin_request():
    """
    Check if the request carries admin-level auth.

    Uses the same get_user() lookup as @api_key_check (supports rio_key
    via query param or JSON body, api_key, JWT, and ADMIN_KEY), then
    checks group membership. Returns True/False without aborting, so
    endpoints can serve a public tier to unauthenticated callers.
    """
    # ADMIN_KEY bypass (same as api_key_check decorator)
    if request.is_json and request.json.get('ADMIN_KEY') == os.getenv('ADMIN_KEY'):
        return True

    rio_user = get_user(request)
    if not rio_user:
        return False

    # Same group-membership query used by @api_key_check
    admin_group = db.session.query(UserGroup.name).join(
        UserGroupUser
    ).join(
        RioUser
    ).filter(
        RioUser.id == rio_user.id,
        UserGroup.name.in_(['Admin', 'TrustedUser'])
    ).first()

    return admin_group is not None


@app.route('/upload_status/', methods=['GET'])
def upload_status():
    """
    Game upload/ingestion pipeline status.

    Public: returns counts of pending, defect, and processed games, plus ongoing games.
    Admin (?rio_key=<admin_key>): adds file-level detail and error messages.
    """
    upload_folder = app.config.get('GAMES_UPLOAD_FOLDER')

    # --- File-based staging area status ---
    pending_files = []
    defect_files = []

    if upload_folder and os.path.isdir(upload_folder):
        try:
            all_files = os.listdir(upload_folder)
            pending_files = sorted(
                f for f in all_files
                if f.endswith('.json') and not f.startswith('defect_')
            )
            defect_files = sorted(
                f for f in all_files
                if f.startswith('defect_') and f.endswith('.json')
            )
        except OSError:
            pass

    # --- Ongoing games from DB ---
    ongoing_games = OngoingGame.query.order_by(desc(OngoingGame.date_time_start)).all()

    # --- Build public response ---
    response = {
        'pending_count': len(pending_files),
        'defect_count': len(defect_files),
        'ongoing_games_count': len(ongoing_games),
        'ongoing_games': [game.to_dict() for game in ongoing_games],
    }

    # --- Admin detail ---
    if _is_admin_request():
        response['pending_files'] = pending_files

        defect_details = []
        for df in defect_files:
            detail = {'filename': df}
            try:
                file_path = os.path.join(upload_folder, df)
                stat = os.stat(file_path)
                detail['file_size_bytes'] = stat.st_size
                detail['modified_time'] = int(stat.st_mtime)

                with open(file_path, 'r') as f:
                    data = json.load(f)
                    detail['error'] = data.get('processing_defect', 'Unknown')
                    detail['game_id'] = data.get('GameID', 'Unknown')
                    detail['home_player'] = data.get('Home Player', 'Unknown')[:8] + '...'
                    detail['away_player'] = data.get('Away Player', 'Unknown')[:8] + '...'
            except Exception:
                detail['error'] = 'Unable to read defect file'
            defect_details.append(detail)

        response['defect_details'] = defect_details

    return jsonify(response), 200


@app.route('/system_status/', methods=['GET'])
def system_status():
    """
    Server health and resource usage.

    Public: basic uptime and health check.
    Admin (?rio_key=<admin_key>): full CPU, memory, disk, and DB stats.
    """
    is_admin = _is_admin_request()

    response = {
        'status': 'ok',
        'timestamp': int(time.time()),
        'platform': platform.system(),
    }

    if not is_admin:
        return jsonify(response), 200

    # --- CPU ---
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count()
    load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else None

    response['cpu'] = {
        'percent': cpu_percent,
        'count': cpu_count,
        'load_avg_1m': round(load_avg[0], 2) if load_avg else None,
        'load_avg_5m': round(load_avg[1], 2) if load_avg else None,
        'load_avg_15m': round(load_avg[2], 2) if load_avg else None,
    }

    # --- Memory ---
    mem = psutil.virtual_memory()
    response['memory'] = {
        'total_gb': round(mem.total / (1024 ** 3), 2),
        'available_gb': round(mem.available / (1024 ** 3), 2),
        'used_gb': round(mem.used / (1024 ** 3), 2),
        'percent': mem.percent,
    }

    # --- Disk ---
    disk = psutil.disk_usage('/')
    response['disk'] = {
        'total_gb': round(disk.total / (1024 ** 3), 2),
        'used_gb': round(disk.used / (1024 ** 3), 2),
        'free_gb': round(disk.free / (1024 ** 3), 2),
        'percent': disk.percent,
    }

    # --- Disk I/O ---
    try:
        disk_io = psutil.disk_io_counters()
        if disk_io:
            response['disk_io'] = {
                'read_mb': round(disk_io.read_bytes / (1024 ** 2), 2),
                'write_mb': round(disk_io.write_bytes / (1024 ** 2), 2),
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
            }
    except Exception:
        pass

    # --- Network I/O ---
    try:
        net_io = psutil.net_io_counters()
        if net_io:
            response['network'] = {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024 ** 2), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024 ** 2), 2),
            }
    except Exception:
        pass

    # --- Process info (this Flask worker) ---
    try:
        proc = psutil.Process()
        proc_mem = proc.memory_info()
        response['process'] = {
            'pid': proc.pid,
            'memory_rss_mb': round(proc_mem.rss / (1024 ** 2), 2),
            'cpu_percent': proc.cpu_percent(interval=0.1),
            'open_files': len(proc.open_files()),
            'threads': proc.num_threads(),
            'uptime_seconds': int(time.time() - proc.create_time()),
        }
    except Exception:
        pass

    # --- Database connection check ---
    try:
        db.session.execute(text('SELECT 1'))
        response['database'] = {'status': 'connected'}
    except Exception as e:
        response['database'] = {'status': 'error', 'error': str(e)}

    return jsonify(response), 200

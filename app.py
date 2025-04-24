import os
os.environ["NUMBA_DISABLE_JIT"] = "1"  # 强制禁用Numba JIT
os.environ["NUMBA_WARNINGS"] = "0"
import numpy as np
import atexit
import logging
import shutil
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from music21 import *
import random
import tempfile
import subprocess
import time
import librosa
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler
import database#数据库文件
import pymysql
from openai import OpenAI
from dotenv import load_dotenv#AI配置
from flasgger import Swagger
from utils import Data  # Assuming you have a similar toast utility
import requests
import json 
import re#智能体调用
import uuid
import load
#http://172.29.235.189:5000/apidocs/  接口查看文档 服务器ip113.45.206.40
# ====================
# 应用初始化配置
# ====================
app = Flask(__name__)
# 全局跨域配置（推荐使用这种最稳的方式）
CORS(app, supports_credentials=True, resources={r"/*": {
    "origins": "*",  # 或改成 ['http://localhost:3000', 'http://你的前端域名']
    "allow_headers": ["Content-Type", "Authorization"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}})
# Swagger 配置 (修改为以下形式)
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
    "blueprint_name": 'custom_swagger'  # 添加唯一名称
}

Swagger(app, 
    template={
        "swagger": "2.0",
        "info": {
            "title": "CalmWave API 文档",
            "description": "心理压力音乐生成系统接口文档",
            "version": "1.0",
            "contact": {
                "email": "1205609108@qq.com"
            }
        },
        "host": "localhost:5000",
        "basePath": "/",
        "schemes": ["http", "https"],
        "definitions": {
            "StandardResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "error"]},
                    "message": {"type": "string"}
                }
            }
        }
    },
    config=swagger_config  # 传入配置
)
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = app.make_response('')
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


# ====================
# 日志系统配置
# ====================
log_handler = RotatingFileHandler(
    'app.log',
    maxBytes=10 * 1024 * 1024,  # 10MB轮转
    backupCount=5,
    encoding='utf-8'
)
log_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
)
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.DEBUG)


# ====================
# 路径处理函数
# ====================
def sanitize_path(path: Path) -> str:
    """处理Windows路径兼容性问题（三重保障）"""
    try:
        resolved = path.resolve().absolute()
        return str(resolved).replace("\\", "/").replace(" ", "_").replace("'", "").encode('utf-8').decode('utf-8')
    except Exception as e:
        logging.error(f"路径处理异常: {str(e)}")
        return str(path)

# ====================
# 音乐生成核心逻辑
# ====================
def generate_base_music(hr, hrv_hf):
    """生成基础和弦进行"""
    bpm = max(60, min(80, int(hr)))
    key = "C" if hrv_hf > 50 else "A minor"

    s = stream.Stream()
    s.append(tempo.MetronomeMark(number=bpm))
    s.append(meter.TimeSignature('4/4'))

    # 和弦库
    chords_major = [
        chord.Chord(["C4", "E4", "G4"], quarterLength=4),
        chord.Chord(["F4", "A4", "C5"], quarterLength=4),
        chord.Chord(["G4", "B4", "D5"], quarterLength=4),
        chord.Chord(["C4", "E4", "G4"], quarterLength=4)
    ]
    chords_minor = [
        chord.Chord(["A3", "C4", "E4"], quarterLength=4),
        chord.Chord(["D4", "F4", "A4"], quarterLength=4),
        chord.Chord(["E4", "G4", "B4"], quarterLength=4),
        chord.Chord(["A3", "C4", "E4"], quarterLength=4)
    ]

    for c in chords_major if "minor" not in key else chords_minor:
        s.append(c)
    return s


def generate_improvisation(base_stream, hrv_hf):
    """生成即兴旋律"""
    melody_stream = stream.Part()
    melody_stream.append(instrument.Piano())

    key = "C" if hrv_hf > 50 else "A"
    is_minor = "minor" in str(base_stream.analyze('key'))

    scl = scale.MinorScale(key) if is_minor else scale.MajorScale(key)
    pitch_set = list(scl.getPitches('C4', 'C6'))

    for c in base_stream.getElementsByClass(chord.Chord):
        for _ in range(random.choice([2, 3, 4])):
            if random.random() < 0.7:
                chosen = random.choice(c.pitches).midi
            else:
                chosen = random.choice(pitch_set).midi
            n = note.Note(chosen)
            n.quarterLength = random.choice([0.5, 1.0]) if hrv_hf < 50 else 1.0
            melody_stream.append(n)
    return melody_stream


# ====================
# 音频处理类
# ====================
class MusicGenerator:
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix='music_'))
        os.makedirs(self.temp_dir, exist_ok=True)
        os.chmod(self.temp_dir, 0o777)
        app.logger.info(f"临时目录创建于: {self.temp_dir}")

    def _convert_midi_to_mp3(self, midi_path: Path, mp3_path: Path):
        """增强转换稳定性"""
        try:
            # 生成中间WAV
            wav_path = midi_path.with_suffix('.wav')
            subprocess.run(
                ['timidity', str(midi_path), '-Ow', '-o', str(wav_path)],
                check=True,
                timeout=30,
                stderr=subprocess.PIPE
            )

            # 转换MP3
            subprocess.run(
                ['ffmpeg', '-y', '-i', str(wav_path),
                 '-acodec', 'libmp3lame', '-b:a', '128k', str(mp3_path)],
                check=True,
                timeout=60,
                stderr=subprocess.PIPE
            )

            wav_path.unlink(missing_ok=True)
        except subprocess.CalledProcessError as e:
            app.logger.error(f"音频转换失败: {e.stderr.decode()}")
            raise RuntimeError("音频转换流程错误")
        except Exception as e:
            app.logger.error(f"未知转换错误: {str(e)}")
            raise

    def generate(self, hr: int, hrv_hf: float) -> str:
        """生成完整音乐作品"""
        try:
            # 生成音乐结构
            base = generate_base_music(hr, hrv_hf)
            improv = generate_improvisation(base, hrv_hf)
            blended = stream.Score([base, improv])

            # 保存文件
            timestamp = int(time.time())
            midi_path = self.temp_dir / f"output_{timestamp}.mid"
            mp3_path = self.temp_dir / f"output_{timestamp}.mp3"

            blended.write('midi', fp=sanitize_path(midi_path))
            self._convert_midi_to_mp3(midi_path, mp3_path)

            # 验证输出文件
            if not mp3_path.exists() or mp3_path.stat().st_size < 10240:
                raise RuntimeError("生成的MP3文件异常")

            return str(mp3_path)
        except Exception as e:
            app.logger.exception("音乐生成失败")
            raise


# ====================
# 可视化数据处理
# ====================
def generate_visual_data(mp3_path):
    """生成可视化数据（强化错误处理）"""
    try:
        y, sr = librosa.load(mp3_path, sr=22050)
        is_fallback = False

        # 主算法：librosa官方方法
        try:
            onset_env = librosa.onset.onset_strength(
                y=y, sr=sr,
                aggregate=np.median,
                hop_length=1024,
                n_fft=4096
            )
            tempo_bpm = librosa.beat.tempo(
                onset_envelope=onset_env.astype(np.float32),
                sr=sr,
                ac_size=8.0
            )[0]
        except Exception as e:
            app.logger.warning(f"主算法失败: {str(e)}")
            is_fallback = True

            # 备用算法：自相关法
            autocorr = librosa.autocorrelate(y)
            skip_samples = max(1, int(0.01 * len(autocorr)))
            valid_autocorr = autocorr[skip_samples:]

            if len(valid_autocorr) < 10:
                raise ValueError("有效自相关数据不足")

            max_index = valid_autocorr.argmax() + skip_samples
            period = max(0.25, min(2.0, max_index / sr))  # 对应30~240BPM
            tempo_bpm = 60 / period

        # 最终校验
        tempo_bpm = max(40, min(120, int(round(tempo_bpm))))
        app.logger.debug(f"BPM计算结果: {tempo_bpm} (备用算法: {is_fallback})")

        return {
            'waveform': y[::1000].tolist(),
            'bpm': tempo_bpm,
            'is_fallback': is_fallback
        }
    except Exception as e:
        app.logger.error(f"可视化数据处理失败: {str(e)}")
        return {'waveform': [], 'bpm': 120}


# ====================
# Flask路由
# ====================
generator = MusicGenerator()


@atexit.register
def cleanup():
    """退出时清理临时目录"""
    try:
        shutil.rmtree(generator.temp_dir, ignore_errors=True)
    except Exception as e:
        app.logger.error(f"清理临时目录失败: {str(e)}")


@app.route('/generate', methods=['POST'])
def handle_generate():
    """主生成接口"""
    """
    生成压力调节音乐
    ---
    tags:
      - 音乐生成
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            pressure:
              type: number
              description: 压力值 (0-100)
              example: 75
    responses:
      200:
        description: 生成成功
        schema:
          type: object
          properties:
            music_url:
              type: string
              example: "/download/output_1234567890.mp3"
            visual_data:
              type: object
              properties:
                waveform:
                  type: array
                  items: number
                bpm:
                  type: integer
                is_fallback:
                  type: boolean
      400:
        description: 参数错误
      500:
        description: 服务器错误
    """
    try:
        data = request.get_json()
        if not data or 'pressure' not in data:
            return jsonify(error="缺少必要参数: pressure"), 400

        pressure = float(data['pressure'])
        hr = pressure * 2 + 60
        hrv_hf = 100 - pressure

        # 获取生成的MP3路径（字符串类型）
        mp3_path_str = generator.generate(hr, hrv_hf)

        # 转换为Path对象获取文件名
        from pathlib import Path
        mp3_path = Path(mp3_path_str)

        return jsonify({
            'music_url': f'/download/{mp3_path.name}',  # 正确使用.name属性
            'visual_data': generate_visual_data(mp3_path_str)
        })
    except ValueError as e:
        app.logger.error(f"参数错误: {str(e)}")
        return jsonify(error="非法参数值"), 400
    except Exception as e:
        app.logger.exception("全局异常")
        return jsonify(error=str(e)), 500


@app.route('/download/<filename>')
def download(filename):
    """
    下载MP3文件
    ---
    tags:
      - 音乐生成
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: The name of the MP3 file to download
        example: example.mp3
    responses:
      200:
        description: MP3 file
        content:
          audio/mpeg:
            schema:
              type: string
              format: binary
      400:
        description: Invalid file type
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: Invalid file type
      404:
        description: File not found
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: Resource not found
      500:
        description: Server error
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: File service error
    """
    try:
        # 安全验证增强
        safe_name = secure_filename(filename.strip())
        if not safe_name.lower().endswith('.mp3'):
            return jsonify(error="Invalid file type"), 400

        file_path = Path(generator.temp_dir) / safe_name

        if not file_path.exists():
            logging.error(f"文件未找到: {file_path}")
            return jsonify(error="Resource not found"), 404

        # 添加缓存控制头
        return send_file(
            file_path,
            mimetype='audio/mpeg',
            conditional=True,
            etag=os.path.getmtime(file_path),
            max_age=0  # 禁用缓存
        )
    except Exception as e:
        logging.error(f"下载失败: {str(e)}", exc_info=True)
        return jsonify(error="File service error"), 500

# ====================
# 数据库获取信息
# ====================
# 获取用户信息
@app.route('/user', methods=['GET'])
def get_user():
    """
    获取用户所有信息
    ---
    tags:
      - 用户管理
    parameters:
      - name: account
        in: query
        type: string
        required: true
        description: 用户账号
        example: "user123"
    responses:
      200:
        description: 用户信息获取成功
        schema:
          type: object
          properties:
            username:
              type: string
              example: "张三"
            account:
              type: string
              example: "user123"
            phone:
              type: string
              example: "13800138000"
      400:
        description: 参数错误
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "缺少 account 参数"
      404:
        description: 用户不存在
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "用户不存在"
    """

    account = request.args.get('account')
    if not account:
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200
    
    user_data = database.get_user(account)
    
    if not user_data:
      return (Data(code="404", msg="用户不存在").__dict__), 200
    return jsonify(user_data.__dict__), user_data.code
#账号密码登录
@app.route('/login', methods=['POST'])
def login():
    """
    账号密码登录
    ---
    tags:
      - 用户管理
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            account:
              type: string
              example: "user123"
            password:
              type: string
              example: "mypassword123"
    responses:
      200:
        description: 登录成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            token:
              type: string
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            user_info:
              type: object
              properties:
                username:
                  type: string
                  example: "张三"
                account:
                  type: string
                  example: "user123"
      400:
        description: 参数错误
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "账号和密码不能为空"
      401:
        description: 认证失败
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "账号或密码错误"
    """

    data = request.get_json()
    print("请求数据：", data)
    account = data.get('account')
    password = data.get('password')

    if not account or not password:
        return jsonify(Data(code="400", msg="账号和密码不能为空").__dict__), 200

    result = database.login_with_account_password(account, password)
    return jsonify(result.__dict__), result.code
#微信登陆
@app.route('/wechat_login', methods=['POST'])
def wechat_login():
    """
    微信登录
    ---
    tags:
      - 用户管理
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            wechat_openid:
              type: string
              description: 微信开放平台openid
              example: "o6_bmjrPTlm6_2sgVt7hMZOPfL2M"
    responses:
      200:
        description: 登录成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            token:
              type: string
              example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            is_new_user:
              type: boolean
              example: false
      400:
        description: 参数错误
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "微信openid不能为空"
      404:
        description: 用户未注册
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "请先完成微信账号注册"
    """
    data = request.get_json()
    wechat_openid = data.get('wechat_openid')

    if not wechat_openid:
        return jsonify(Data(code="400", msg="参数不能为空").__dict__), 200

    result = database.login_with_wechat(wechat_openid)
    return jsonify(result.__dict__), result.code

#注册用户
@app.route('/register', methods=['POST'])
def register_user():
    """
    用户注册
    ---
    tags:
      - 用户管理
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              example: "张三"
            account:
              type: string
              example: "user123"
            phone:
              type: string
              example: "13800138000"
            password:
              type: string
              example: "mypassword123"
    responses:
      200:
        description: 注册成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            user_id:
              type: integer
              example: 123
      400:
        description: 参数错误
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "参数不完整"
      409:
        description: 账号已存在
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "账号已被注册"
    """
    data = request.get_json()
    print(data["account"]+"resiger")
    if not all(k in data for k in ("username", "account", "phone","password")):
        return jsonify(Data(code="400", msg="参数不完整").__dict__), 200

    result = database.add_user(data["username"], data["account"], data["phone"], data["password"])
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
class UserNotFoundError(Exception):
    """自定义用户不存在异常"""
    def __init__(self, account):
        self.account = account
        super().__init__(f"Account {account} exit")
#用户注销
@app.route('/user_delete', methods=['GET'])
def delete_user_data():
    """
用户注销账户
---
tags:
  - 用户管理
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      properties:
        account:
          type: string
          description: 用户账号标识
responses:
  200:
    description: 用户数据删除成功
  400:
    description: 请求参数缺失（账号不能为空）
  500:
    description: 服务器内部错误
"""

    data = request.get_json()
    account = data.get('account')
    
    if  account is None:
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200

    result = database.delete_user(account)
       
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
#压力记录删除
@app.route('/pressure_delete', methods=['GET'])
def delete_pressure_data():
    """
删除用户压力记录
---
tags:
  - 用户压力数据管理
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      properties:
        account:
          type: string
          description: 用户账号标识
responses:
  200:
    description: 压力记录删除成功
  400:
    description: 请求参数缺失（账号不能为空）
  500:
    description: 服务器内部错误
"""

    data = request.get_json()
    account = data.get('account')
    
    if  account  is None:
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200

    result = database.delete_pressure_data_form(account)
       
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code 
#蓝牙记录删除
@app.route('/device/delete', methods=['POST'])
def delete_device_connection_form():
    """
    删除用户蓝牙设备连接记录
    ---
    tags:
      - 用户设备管理
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              account:
                type: string
                description: 用户账号标识
    responses:
      200:
        description: 蓝牙设备连接记录删除成功
      400:
        description: 请求参数缺失（账号不能为空）
      500:
        description: 服务器内部错误
    """
    try:
        if not request.is_json:
            return jsonify(Data(code="400", msg="请求体必须是 JSON 格式").__dict__), 200

        data = request.get_json()
        account = data.get('account')

        if not account:
            return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200

        result = database.delete_device_connection_form(account)
        status_code = 200 if result.code == "200" else 500
        return jsonify(result.__dict__), status_code

    except Exception as e:
        return jsonify(Data(code="500", msg=f"服务器内部错误: {str(e)}").__dict__), 500
# 记录设备连接历史
@app.route('/device/connect', methods=['POST'])
def connect_device():
    """
    记录设备连接历史
    ---
    tags:
      - 用户设备管理
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            account:
              type: string
              example: "user123"
            device_id:
              type: string
              example: "device_001"
            status:
              type: string
              enum: ["connected", "disconnected"]
              example: "connected"
            device_name:
              type: string
              example: "小米手环7"
            mac_address:
              type: string
              example: "00:1A:7D:DA:71:13"
    responses:
      200:
        description: 记录成功
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            connection_id:
              type: integer
              example: 456
      400:
        description: 参数错误
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "Missing parameters"
    """
    data = request.get_json()  # 更安全的获取方式
    if not data or not all(k in data for k in ("account", "device_id", "status", "device_name", "mac_address")):
        return jsonify(Data(code="400", msg="填入数值不能为空").__dict__), 200
    
    # 不再需要try-catch，交由Flask处理
    result = database.record_device_connection(
        data["account"], data["device_id"], data["status"],
        data["device_name"], data["mac_address"]
    )
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code



# 存储压力数据接口 压力1-5
@app.route('/store_pressure', methods=['POST'])
def store_pressure():
    """
    存储用户压力数据
    ---
    tags:
      - 用户压力数据管理
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            account:
              type: string
              example: "user123"
            pressure_value:
              type: number
              example: 65.5
            device_id:
              type: string
              required: false
              example: "device_001"
    responses:
      200:
        description: 存储结果
        schema:
          $ref: '#/definitions/StandardResponse'
      400:
        description: 参数缺失
    """
    data = request.get_json()
    account = data.get('account')
    pressure_value = data.get('pressure_value')
    device_id = data.get('device_id', None)


    if not account or pressure_value is None:
        return jsonify(Data(code="400", msg="账号和压力值不能为空").__dict__), 200

    result = database.store_pressure_data(account, pressure_value, device_id)
       
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
#测量基准数值
@app.route('/baseline_phy_signal/store',methods=['POST'])
def store_baseline_phy_signal():
    """
测量并存储用户基准生理信号数值
---
tags:
  - 生理信号
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      properties:
        account:
          type: string
          description: 用户账号标识
        Heart_rate:
          type: number
          description: 心率（单位：次/分钟）
        Blood_pressure:
          type: string
          description: 血压（格式示例：120/80）
        skin_conductance:
          type: number
          description: 皮肤电导值（单位：μS）
        skin_temperature:
          type: number
          description: 皮肤温度（单位：摄氏度）
responses:
  200:
    description: 成功存储用户基准生理信号数据
  400:
    description: 请求参数缺失（账号或测量值为空）
  500:
    description: 服务器内部错误
"""

    data = request.get_json()
    account = data.get('account')
    Heart_rate =data.get('Heart_rate')
    Blood_pressure=data.get('Blood_pressure')
    skin_conductance=data.get('skin_conductance')
    skin_temperature=data.get('skin_temperature')

    if not account or Heart_rate is None or Blood_pressure is None or skin_conductance is None or skin_temperature is None:
        return jsonify(Data(code="400", msg="账号和测量数值不能为空").__dict__), 200

    result = database.record_baseline_physiological_signals(account,Heart_rate,Blood_pressure,skin_conductance ,skin_temperature)
       
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
# 获取基准数值
@app.route('/baseline_phy_signal/get', methods=['GET'])
def get_baseline_phy_signal():
    """
获取用户基准生理信号数值
---
tags:
  - 生理信号
parameters:
  - in: query
    name: account
    required: true
    schema:
      type: string
    description: 用户账号标识，用于获取其基准生理信号数据
responses:
  200:
    description: 成功返回用户基准生理信号数据
  400:
    description: 请求参数缺失（账号不能为空）
  500:
    description: 服务器内部错误
"""

    args = request.args
    print(args)  # 打印查询参数，查看是否正确传递

    account = args.get('account')
  
    if  account is None:
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200

    result = database.get_baseline_physiological_signals(account)
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code

# 获取同一天的压力数据接口
@app.route('/get_pressure', methods=['GET'])
def get_pressure():
    """
    获取用户指定日期的压力数据
    ---
    tags:
      - 用户压力数据管理
    parameters:
      - name: account
        in: query
        type: string
        required: true
        description: 用户账号
        example: "user123"
      - name: date
        in: query
        type: string
        required: true
        description: 查询日期 (YYYY-MM-DD格式)
        example: "2023-10-15"
    responses:
      200:
        description: 查询成功
        schema:
          type: object
          properties:
            status:
              type: string
              enum: ["success", "error"]
              example: "success"
            data:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    example: 1
                  account:
                    type: string
                    example: "user123"
                  pressure_value:
                    type: number
                    format: float
                    example: 75.5
                  record_time:
                    type: string
                    format: date-time
                    example: "2023-10-15 14:30:00"
                  device_id:
                    type: string
                    example: "device_001"
      400:
        description: 参数错误
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            message:
              type: string
              example: "账号和日期不能为空"
      404:
        description: 无数据
        schema:
          type: object
          properties:
            status:
              type: string
              example: "success"
            data:
              type: array
              items: {}
              example: []
    """
    args = request.args

    account = args.get('account')
    date = args.get('date')


    if not account or not date:
        return jsonify(Data(code="400", msg="账号和日期不能为空").__dict__), 200

    result = database.get_pressure_data(account, date)
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
#AI聊天
# 智能体的个人令牌(一个月过期2025/5/19)，botid
bot_id = '7494550975282839586'
api_key = 'pat_LPhpdhwRSQWxAirw1qSBScRQykfTIkWYk9XEnSPwI9OkBBAGD7zVQZVbAMbvwpFa'
# 加载环境变量
load_dotenv('D:\Psystem\Databased\DataBase\music\CalmwaveAPI.env')#env中存放了API
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"  # 替换为硅基流动的实际地址
# 初始化deeepseek客户端
client = OpenAI(api_key=os.getenv("SILICONFLOW_API_KEY"),
                 base_url=SILICONFLOW_BASE_URL,  # 关键：覆盖默认的 OpenAI 地址
                )
# 使用字典存储不同用户的对话历史
user_sessions = {}
#调用智能体 发起对话
base_url = 'https://api.coze.cn/v3/chat'

headers = {
    "Authorization": f"Bearer {api_key}",
    'Content-Type': 'application/json'
}

"""
        # 调用API（始终发送完整历史）
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            messages=user_sessions[account][-6:],  # 限制最近6条 
            temperature=0.7,
            max_tokens=500
        )

        # 添加AI回复到历史
        ai_response = response.choices[0].message.content
        user_sessions[account].append({"role": "assistant", "content": ai_response})

        
        """
#更新头像图片
#request.get_json() 无法获取文件！
#你用的是 request.get_json()，它只适用于 application/json 类型的请求。头像上传是通过 multipart/form-data 提交的，所以应该使用 request.form 和 request.files。
#只允许上传：.png .jpg .jpeg

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#上传头像
@app.route('/upload-avatars', methods=['POST'])
def upload_avatars():
    """
上传用户头像文件（支持批量，返回 OSS 图片链接数组）
---
tags:
  - 用户管理
consumes:
  - multipart/form-data
parameters:
  - in: formData
    name: avatar
    required: true
    type: array
    items:
      type: file
    description: 头像图片文件数组，仅支持 png/jpg/jpeg 格式
responses:
  200:
    description: 上传成功，返回头像图片的公开 URL 数组
    content:
      application/json:
        schema:
          type: object
          properties:
            code:
              type: string
              example: "200"
            msg:
              type: string
              example: 所有用户头像上传成功
            result:
              type: array
              items:
                type: string
                example: https://your-bucket.oss-cn-region.aliyuncs.com/avatars/xxx.jpg
  400:
    description: 请求参数错误（如缺少图片或格式不支持）
  500:
    description: 服务器内部错误
    """
    try:
        files = request.files.getlist('avatar')
        if not files or len(files) == 0:
            return jsonify(Data(code="400", msg="未找到图片", result=None).__dict__), 200

        urls = []
        for file in files:
            if not allowed_file(file.filename):
                return jsonify(Data(code="400", msg="仅支持 png/jpg/jpeg 格式图片", result=None).__dict__), 200
            
            ext = file.filename.rsplit('.', 1)[-1]
            filename = f"avatars/{uuid.uuid4()}.{ext}"
            image_url = load.upload_image_to_oss(file, filename)
            urls.append(image_url)

        return jsonify(Data(code="200", msg="所有用户头像上传成功", result=urls).__dict__), 200
    
    except Exception as e:
        return jsonify(Data(code="500", msg=f"服务异常: {str(e)}", result=None).__dict__), 500

#存储头像
@app.route('/store_avatar', methods=['POST'])
def store_avatar():
    """
存储用户头像与昵称
---
tags:
  - 用户管理
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      properties:
        username:
          type: string
          description: 用户昵称
        account:
          type: string
          description: 用户账号标识
        avatar_url:
          type: string
          description: 用户头像图片的 URL 地址
responses:
  200:
    description: 用户头像与昵称保存成功
  400:
    description: 请求参数缺失（头像不能为空）
  500:
    description: 服务器内部错误
"""
    try:
        data = request.get_json()
        username = data.get("username")
        account = data.get("account")  # 默认用户
        avatar_url=data.get("avatar_url")
        
        if not avatar_url:
            return jsonify(Data(code="400", msg="图片不能为空").__dict__),200
        result=database.update_avatar(account,avatar_url,username)

        return jsonify(Data(code="200", msg="头像和昵称存储成功").__dict__),200

    except Exception as e:
        return jsonify(Data(code="500", msg=f"服务异常: {str(e)}").__dict__), 500
#获取头像
@app.route('/get_avatar', methods=['GET'])
def get_avatar():
  """
获取用户头像和昵称
---
tags:
  - 用户管理
parameters:
  - in: query
    name: account
    required: true
    schema:
      type: string
    description: 用户账号标识，用于获取头像
responses:
  200:
    description: 成功返回用户头像和昵称
  400:
    description: 请求参数缺失（账号不能为空）
  500:
    description: 服务器内部错误"""
  
  try:
        args = request.args
       
        account = args.get("account")  # 默认用户

        if not account:
            return jsonify(Data(code="400", msg="账号不能为空").__dict__),200
        result=database.get_avatar(account)

        status_code = 200 if result.code == "200" else 500
        return jsonify(result.__dict__), status_code
  except Exception as e:
       return jsonify(Data(code="500", msg=f"服务异常: {str(e)}").__dict__), 500


def extract_json_from_nested_content(content):
    try:
        # 先解析第一层 JSON（实际是一个 JSON 字符串）
        outer = json.loads(content)
        output = outer.get("output", "")
        
        # 检查是否包含 Markdown 格式的 JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', output, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))  # 提取并解析 JSON
        
        # 尝试解析无 markdown 的 JSON（如果没有 Markdown 格式的包装）
        brace_match = re.search(r'\{.*\}', output, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group())

    except Exception as e:
        print(f"[DEBUG] extract_json_from_nested_content 错误: {str(e)}")

    return None
def extract_analysis_result_from_messages(messages):
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        if role != "assistant":
            continue

        try:
            # 尝试解析嵌套 JSON 格式
            outer = json.loads(content)
            if isinstance(outer, dict) and "output" in outer:
                match = re.search(r'\{.*?\}', outer["output"], re.DOTALL)
                if match:
                    return json.loads(match.group())
        except:
            pass
    return None

def call_coze_bot(question_text):
    data = {
        "bot_id": bot_id,
        "user_id": "jiangwp",
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": question_text,
                "content_type": "text"
            }
        ]
    }

    # 发送请求以启动对话
    response = requests.post(base_url, headers=headers, data=json.dumps(data))
    if response.status_code != 200:
        raise Exception(f"启动对话失败: {response.text}")

    response_data = response.json()
    chat_id = response_data['data']['id']
    conversation_id = response_data['data']['conversation_id']

    # 轮询直到生成完成
    retrieve_url = f"{base_url}/retrieve?conversation_id={conversation_id}&chat_id={chat_id}"
    while True:
        status_response = requests.get(retrieve_url, headers=headers)
        if status_response.status_code != 200:
            raise Exception(f"查询状态失败: {status_response.text}")

        status_data = status_response.json()
        if status_data['data']['status'] == 'completed':
            break
        time.sleep(1)

    # 获取最终 message 列表
    msg_url = f"{base_url}/message/list?chat_id={chat_id}&conversation_id={conversation_id}"
    msg_response = requests.get(msg_url, headers=headers)
    if msg_response.status_code != 200:
        raise Exception(f"获取消息失败: {msg_response.text}")

    # 只返回最终的 data 字段（即智能体的全部回答）
    return msg_response.json()['data']
# 解析智能体的输出
def parse_bot_output(output):
    return json.loads(output)
@app.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    """
智能体解析用户提问生成音乐推荐 Prompt
---
tags:
  - 音乐推荐
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      properties:
        question:
          type: string
          description: 用户提问或倾诉内容，将由智能体解析
        account:
          type: string
          description: 用户账号标识，默认 default
responses:
  200:
    description: 成功生成音乐推荐 prompt，并返回对话历史
    content:
      application/json:
        schema:
          type: object
          properties:
            code:
              type: string
              example: "200"
            msg:
              type: string
              example: AI分析成功
            result:
              type: object
              properties:
                answer:
                  type: string
                  example: 猜你喜欢：lofi calm medium 加点节奏感
                history:
                  type: array
                  description: 用户与 AI 的对话历史（不包含 system 开头）
                  items:
                    type: object
                    properties:
                      role:
                        type: string
                        example: user / assistant
                      content:
                        type: string
  400:
    description: 参数错误（问题为空）
  500:
    description: 服务异常
"""

  
    try:
        data = request.get_json()
        user_question = data.get("question", "")
        account = data.get("account", "default")  # 默认用户
        
        if not user_question:
            return jsonify(Data(code="400", msg="问题不能为空").__dict__), 200
        

        # 获取或初始化该用户的对话历史
        if account not in user_sessions:
            user_sessions[account] = [
                {"role": "system", "content": "你是根据用户聊天记录"}
            ]

        # 添加用户问题到历史
        user_sessions[account].append({"role": "user", "content": user_question})
        
        

       
        
        # 调用 Coze Bot 并打印完整响应
        prompts_response = call_coze_bot(user_question)
        #print("[DEBUG] prompts_response 完整结构:")
        print(json.dumps(prompts_response, indent=2, ensure_ascii=False))

        parsed_json = None
        for message in prompts_response:
            content = message.get("content", "")
            if content:
                parsed_json = extract_json_from_nested_content(content)
                if parsed_json:
                    break

        #print("[DEBUG] parsed_json 最终结果:")
        #print(parsed_json)

        if parsed_json is None:
            return jsonify({"code": "500", "msg": "未能解析有效的推荐数据"}), 200

        # 提取数据（提供默认值）
        genre = parsed_json.get('genre', '')
        mood = parsed_json.get('mood', '')
        tempo = parsed_json.get('tempo', '')
        additional_requirements = parsed_json.get('additional_requirements', '')


        like = f"{genre} {mood} {tempo} {additional_requirements}".strip()
        """
        if like is None:
            print("[DEBUG] parsed_json 最终结果:")
            print(parsed_json)
        """

        # 存储推荐信息（假设 database 方法已定义）
        prompts_result = database.store_personal_prompts(account, genre, mood, tempo, additional_requirements)

        result = {
            "answer": f"猜你喜欢：{like}"
            
        }

        return jsonify(Data(code="200", msg="AI分析成功", result=result).__dict__)

    except Exception as e:
        print(f"[ERROR] 服务异常: {str(e)}")
        return jsonify(Data(code="500", msg=f"服务异常: {str(e)}", result=None).__dict__), 500
#获取用户的个性化prompts
@app.route('/presonal_prompts/get', methods=['GET'])   
def get_presonal_prompts():
    """
获取用户个性化Prompts
---
tags:
  - 音乐推荐
parameters:
  - in: query
    name: account
    required: true
    schema:
      type: string
    description: 用户账号标识，用于获取个性化推荐内容
responses:
  200:
    description: 成功返回用户个性化Prompts
  400:
    description: 请求参数缺失（账号不能为空）
  500:
    description: 服务器内部错误
"""

    args = request.args

    account = args.get('account')
  
    if not account :
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200

    result = database.get_personal_prompts(account)
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code


#间隔生成音乐 间隔三分钟，要改去database文件改
@app.route('/music/check_music_create', methods=['GET'])  
def check_music_create():
    """
检查并生成音乐（每3分钟生成一次）
---
tags:
  - 音乐生成
parameters:
  - in: query
    name: account
    required: true
    schema:
      type: string
    description: 用户账号标识，用于判断是否满足生成间隔条件（默认间隔为3分钟）
responses:
  200:
    description: 成功生成或返回已有音乐
  400:
    description: 请求参数缺失（账号不能为空）
  500:
    description: 服务器内部错误
notes:
  如果需要修改生成间隔，请到 database 文件中修改相关逻辑。
"""


    args = request.args

    account = args.get('account')
    if not account :
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200
    result=database.create_music(account)
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code



#获取音乐  音乐获取有返回url无则返回none
@app.route('/music/get_music', methods=['GET'])  
def get_music():
    """
    获取用户生成的音乐资源
    ---
    tags:
      - 音乐生成
    parameters:
      - in: query
        name: account
        required: true
        schema:
          type: string
        description: 用户账号标识，用于查询已生成的音乐文件
    responses:
      200:
        description: 获取成功，返回音乐文件的 URL
      404:
        description: 未找到用户的音乐资源（可能尚未生成）
      400:
        description: 请求参数缺失（账号不能为空）
      500:
        description: 服务器内部错误
    """
    args = request.args
    account = args.get('account')

    if not account:
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 200

    result = database.get_music(account)
    if result.code == "200":
        status_code = 200  
    elif result.code == "404":
        status_code = 404
    else:
        status_code = 500    

    return jsonify(result.__dict__), status_code

#意见反馈表提交
@app.route('/store_feedback_data', methods=['POST'])  
def store_feedback_data():
    """
提交意见反馈
---
tags:
  - 用户反馈
parameters:
  - in: body
    name: body
    required: true
    schema:
      type: object
      properties:
        selectedType:
          type: string
          description: 反馈类型（如功能建议、BUG反馈等）
        feedbackContent:
          type: string
          description: 反馈的具体内容
        contact:
          type: string
          description: 用户联系方式（邮箱/电话）
        account:
          type: string
          description: 用户账号标识
        images:
          type: array
          items:
            type: string
          description: 附件图片（Base64编码或URL数组）
responses:
  200:
    description: 意见反馈提交成功
  400:
    description: 请求参数缺失
  500:
    description: 服务器错误
"""
  
    data = request.get_json()
    selectedType =data.get('selectedType')
    feedbackContent=data.get('feedbackContent')
    contact=data.get('contact')
    account =data.get('account')
    images=data.get('images')
    if not account or selectedType is None or feedbackContent is None or contact is None :
        return jsonify(Data(code="400", msg="账号和提交值不能为空").__dict__), 200

    result = database.store_feedback_data(selectedType,feedbackContent,contact,account,images)
       
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
#报表数据获取
@app.route('/get_day_pressure', methods=['GET'])  
def get_day_pressure():
    """
获取用户某日压力数据
---
tags:
  - 用户压力数据管理
parameters:
  - in: query
    name: account
    required: true
    schema:
      type: string
    description: 用户账号标识
  - in: query
    name: date
    required: true
    schema:
      type: string
    description: 查询的日期（格式：YYYY-MM-DD）
responses:
  200:
    description: 成功返回压力数据
  400:
    description: 请求参数缺失（账号或日期为空）
  500:
    description: 服务器内部错误
"""

    args = request.args

    account = args.get('account')
    date=args.get('date')
  
    if not account or date is None :
        return jsonify(Data(code="400", msg="账号与日期不能为空").__dict__), 200

    result = database.get_day_pressure(account,date)
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code




# ====================
# 启动入口
# ====================
if __name__ == '__main__':
    app.logger.info("服务启动初始化完成")
    app.run(host='0.0.0.0', port=5000, debug=True)
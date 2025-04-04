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
#http://113.45.206.40:5000/apidocs/  接口查看文档 服务器ip113.45.206.40
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
        return jsonify(Data(code="400", msg="账号不能为空").__dict__), 400
    
    user_data = database.get_user(account)
    
    if not user_data:
      return (Data(code="404", msg="用户不存在").__dict__), 400
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
        return jsonify(Data(code="400", msg="账号和密码不能为空").__dict__), 400

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
        return jsonify(Data(code="400", msg="参数不能为空").__dict__), 400

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
        return jsonify(Data(code="400", msg="参数不完整").__dict__), 400

    result = database.add_user(data["username"], data["account"], data["phone"], data["password"])
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
class UserNotFoundError(Exception):
    """自定义用户不存在异常"""
    def __init__(self, account):
        self.account = account
        super().__init__(f"Account {account} exit")

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
        return jsonify(Data(code="400", msg="填入数值不能为空").__dict__), 400
    
    # 不再需要try-catch，交由Flask处理
    result = database.record_device_connection(
        data["account"], data["device_id"], data["status"],
        data["device_name"], data["mac_address"]
    )
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code



# 存储压力数据接口
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
        return jsonify(Data(code="400", msg="账号和压力值不能为空").__dict__), 400

    result = database.store_pressure_data(account, pressure_value, device_id)
       
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
    args = request.parsed_args

    account = args['account']
    date = args['date']


    if not account or not date:
        return jsonify(Data(code="400", msg="账号和日期不能为空").__dict__), 400

    result = database.get_pressure_data(account, date)
    status_code = 200 if result.code == "200" else 500
    return jsonify(result.__dict__), status_code
#AI聊天
# 加载环境变量
load_dotenv('D:\Psystem\Databased\DataBase\music\CalmwaveAPI.env')#env中存放了API
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"  # 替换为硅基流动的实际地址
# 初始化deeepseek客户端
client = OpenAI(api_key=os.getenv("SILICONFLOW_API_KEY"),
                 base_url=SILICONFLOW_BASE_URL,  # 关键：覆盖默认的 OpenAI 地址
                )
# 使用字典存储不同用户的对话历史
user_sessions = {}

@app.route('/api/ask-ai', methods=['POST'])
def ask_ai():
    """
    压力疏导AI对话
    ---
    tags:
      - AI聊天
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            question:
              type: string
            user_id:  # 新增用户标识
              type: string
    responses:
      200:
        description: 带对话历史的AI回复
    """
    try:
        data = request.get_json()
        user_question = data.get("question", "")
        user_id = data.get("user_id", "default")  # 默认用户
        
        if not user_question:
            return jsonify(Data(code="400", msg="问题不能为空").__dict__), 400

        # 获取或初始化该用户的对话历史
        if user_id not in user_sessions:
            user_sessions[user_id] = [
                {"role": "system", "content": "你是心理疏导助手小荔，用温暖、关怀的语气与用户交流，帮助缓解压力。"}
            ]

        # 添加用户问题到历史
        user_sessions[user_id].append({"role": "user", "content": user_question})
        print("已经调用AI接口")

        # 调用API（始终发送完整历史）
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            messages=user_sessions[user_id][-6:],  # 限制最近6条 
            temperature=0.7,
            max_tokens=500
        )

        # 添加AI回复到历史
        ai_response = response.choices[0].message.content
        user_sessions[user_id].append({"role": "assistant", "content": ai_response})

        result = {
            "answer": ai_response,
            "history": user_sessions[user_id][1:]  # 不包括 system 的首条
        }
        return jsonify(Data(code="200", msg="AI回复成功", result=result).__dict__)

    except Exception as e:
        return jsonify(Data(code="500", msg=f"服务异常: {str(e)}", result=None).__dict__), 500
            


# ====================
# 启动入口
# ====================
if __name__ == '__main__':
    app.logger.info("服务启动初始化完成")
    app.run(host='0.0.0.0', port=5000, debug=True)
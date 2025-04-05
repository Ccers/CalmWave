import pymysql
import pymysql.cursors
import bcrypt
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash
from utils import Data #返回值结构体

class UserNotFoundError(HTTPException):  # 改为继承HTTPException
    code = 404  # 直接绑定状态码
    description = "User not found"
    
    def __init__(self, account):
        super().__init__()
        self.description = f"User {account} not found"
"""
mydb = pymysql.connect(
    host="localhost",
    user="root",
    passwd="123456",
    database="CalmWave_DataBases" #所创建数据库的名字
    charset': 'utf8mb4'
)
mycursor = mydb.cursor()
"""
#mycursor.execute("Create DATABASE CalmWave_DAtaBases")

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'CalmWave_Databases',
    'charset': 'utf8mb4'
}
def get_db_connection():
    return pymysql.connect(**DB_CONFIG)
#获取用户信息
def get_user(account):
    connection=get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM user WHERE account =%s",(account,))
            return cursor.fetchone()
    finally:
        connection.close()
# 加密用户密码
def hash_password(password: str) -> bytes:
    """对密码进行加密，返回字节串"""
    salt = bcrypt.gensalt()  # 生成随机盐
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)  # 哈希加密
    return hashed_password  # 返回字节串

#检查登录
def check_password(stored_password: bytes, provided_password: str) -> bool:
    """验证用户输入的密码是否正确"""
    # 存储的密码是字节串，提供的密码需要转换为字节串
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)


#账户登录
# 账号密码登录
def login_with_account_password(account:str, password:str)->Data:
    connection = get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM user WHERE account = %s"
            cursor.execute(sql, (account,))
            user = cursor.fetchone()

            if not user:
                return Data(code="404", msg="用户不存在", result=None)
            

            # 验证密码
            if check_password(user['password'], password):
                # 登录成功，返回账号和用户名
                user_info = {
                    
                    "username": user['username'],
                    "account": user['account']
                }
                return Data(code="200", msg="登录成功", result=user_info)
            else:
                return Data(code="401", msg="密码错误", result=None)
    finally:
        connection.close()

#微信登陆
# 微信登录
def login_with_wechat(wechat_openid:str)->Data:
    connection = get_db_connection()
    try:
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            # 查询用户
            sql = "SELECT * FROM user WHERE wechat_openid = %s"
            cursor.execute(sql, (wechat_openid,))
            user = cursor.fetchone()

            if not user:
                register_wechat_user(wechat_openid)
                # 再次查询用户信息
                cursor.execute(sql, (wechat_openid,))
                user = cursor.fetchone()

                
            sql = "SELECT * FROM user WHERE wechat_openid = %s"
            cursor.execute(sql, (wechat_openid,))
            user = cursor.fetchone()        

            if user:
            # 登录成功，返回账号和用户名
                user_info = {
                   
                    "username": user['username'],
                    "account": user['account']
                }
                return Data(code="200", msg="登录成功", result=user_info)
            else:
                return Data(code="401", msg="注册登录失败", result=None)
    finally:
        connection.close()
def register_wechat_user(wechat_openid:str, username:str=None, phone:str=None)-> Data:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查微信 OpenID 是否已注册
            sql_check = "SELECT * FROM user WHERE wechat_openid = %s"
            cursor.execute(sql_check, (wechat_openid,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                return Data(code="500", msg=f"微信账号已注册", result=None)

            # 插入新用户
            account=wechat_openid#将用户的微信戳作为账号主键
            username=wechat_openid#将用户的微信戳作为账号主键
            phone=wechat_openid#将用户的微信戳作为账号主键

            sql_insert = """
            INSERT INTO user (username, wechat_openid, phone, account,created_at) 
            VALUES (%s, %s, %s, %s ,NOW())
            """
            cursor.execute(sql_insert, (username, wechat_openid, phone,account))
            connection.commit()
            return Data(code="200", msg="微信用户注册成功", result=None)
    finally:
        connection.close()


#用户添加
def add_user(username:str, account:str, phone:str, password:str)->Data:
    hashed_password = hash_password(password)#对用户密码加密并存储加密后的密码
    connection =get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM user WHERE username = %s OR phone=%s)", (username,phone))
            user_exists = cursor.fetchone()[0]  # 这会返回True/False
            if user_exists ==False:
                sql ="""INSERT INTO user (username, account, phone,password)
                VALUES (%s, %s, %s, %s)"""
                cursor.execute(sql,(username, account, phone,hashed_password))
                connection.commit()
                print(account+"用户成功注册")
        return Data(code="200", msg="用户成功注册", result=None)
    except pymysql.err.IntegrityError:
        print("账号已存在")
        return Data(code="500", msg="账号已存在", result=None)
    finally:
        connection.close()

# 登录时调用将提供的密码和存储的密码进行比较
def check_password(stored_password: str, provided_password: str) -> bool:
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))


#添加新的蓝牙设备
def add_bluetooth_device(device_id:str, device_name:str,mac_address:str)->Data:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "INSERT INTO bluetooth_device (device_id, device_name,mac_address,last_connected_time) VALUES (%s, %s,%s,Now())"
            cursor.execute(sql, (device_id, device_name,mac_address))
        connection.commit()
        return Data(code="200", msg="蓝牙设备添加成功", result=None)
    
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None)
    finally:
        connection.close()


#蓝牙设备链接记录
def record_device_connection(account:str,device_id:str,status:str,device_name:str,mac_address:str)-> Data:
    connection =get_db_connection()
    try:
        with connection.cursor() as cursor:
            if status=="已连接":
                # 检查 device_id 是否存在
                cursor.execute("SELECT EXISTS(SELECT 1 FROM bluetooth_device WHERE device_id = %s)", (device_id,))
                device_exists= cursor.fetchone()[0]                
                if device_exists == False:
                    add_bluetooth_device(device_id, device_name,mac_address)
                # 检查用户是否存在（这里会抛出UserNotFoundError）
                cursor.execute("SELECT EXISTS(SELECT 1 FROM user WHERE account = %s)", (account,))
                user_ex=cursor.fetchone()[0]  
                if  user_ex==True:
                    print("用户存在")
                    sql="""INSERT INTO device_connection_history (account, device_id, connection_time, connection_status)
                    VALUES (%s, %s, NOW(), '已连接')
                    """
                    cursor.execute(sql,(account, device_id)) 
                else:
                    raise UserNotFoundError(account)
                
               
            elif status=="已断开":
                sql = """ UPDATE device_connection_history 
                    SET disconnection_time = NOW(), connection_status = '已断开'
                    WHERE account = %s AND device_id = %s AND connection_status = '已连接'
                    """
                #print("断开链接 account:"+account )
                cursor.execute(sql,(account,device_id))
                sql="""UPDATE bluetooth_device SET last_connected_time = NOW() WHERE device_id = %s"""
                cursor.execute(sql,(device_id))

        connection.commit()
        return Data(code="200", msg="设备添加成功", result=None)
    
    except pymysql.Error as e:
        connection.rollback()
        raise  # 重新抛出数据库异常
    finally:
        connection.close()
# 存储压力数据
def store_pressure_data(account: str, pressure_value: float, device_id: str = None) -> Data:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO pressure_data (account, pressure_value, record_time, device_id)
            VALUES (%s, %s, NOW(), %s)
            """
            cursor.execute(sql, (account, pressure_value, device_id))
        connection.commit()
      
        return Data(code="200", msg="压力数据存储成功", result=None)
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None)
    finally:
        connection.close()
# 获取同一天的压力数据
def get_pressure_data(account: str,  date:str)-> Data:
    """
    :param account: 用户账号 
    :param date: 查询的日期 (格式: 'YYYY-MM-DD')
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 基础 SQL 语句
            sql = """
            SELECT * FROM pressure_data
            WHERE account = %s AND DATE(record_time) = %s
            """
            params = [account, date]

            cursor.execute(sql, params)
            result = cursor.fetchall()

        return Data(code="200", msg="压力数据获取成功", result=result)
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None)
    finally:
        connection.close()
#聊天


#login_with_wechat("12345")
#add_user("小明","xm123","13800138000","145263")
#get_user("xm123")

#store_pressure_data("xm123","82","1")
#get_pressure_data("xm123","2025-03-29")
#record_device_connection("xm123","001","已断开","CE","device2")
"""
mycursor.execute("SHOW DATABASES")
for x in mycursor:
  print(x)  
mycursor.execute("CREATE TABLE stu_table2(id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(255), age INT,score INT)")#设置id为主键（PRIMARY KEY
mycursor.execute("SHOW TABLES") 
for x in mycursor:
    print(x)
"""
"""
import pymysql
 
mydb = pymysql.connect(     #创建连接mysql
    host="localhost",       #主机名默认localhost
    user="root",            #用户名默认root
    passwd="123456",      #按装MySQL时候设置的密码
    database="student_id" #所创建数据库的名字
)
 
mycursor = mydb.cursor()    #获取连接的cursor(游标对象)，才能进行各种操作
mycursor.execute("SELECT * FROM stu_table2")
myresult=mycursor.fetchall()#fetchall用来获取
for x in myresult:
    print(x)
"""
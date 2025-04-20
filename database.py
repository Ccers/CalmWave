import pymysql
import pymysql.cursors
import bcrypt
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash
from utils import Data #返回值结构体
import json
import random
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
#删除压力数据
def delete_pressure_data_form(account: str) -> Data:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. 检查用户是否存在（更可靠的检查方式）
            cursor.execute("SELECT account FROM user WHERE account = %s", (account,))
            user_record = cursor.fetchone()
            
            if not user_record:  # 更明确的检查方式
                return Data(code="404", msg=f"用户 {account} 不存在", result=None)
            
            # 2. 删除压力数据
            try:
                cursor.execute("DELETE FROM pressure_data WHERE account = %s", (account,))
                affected_rows = cursor.rowcount
                
                # 3. 验证删除结果（可选）
                cursor.execute("SELECT COUNT(1) FROM pressure_data WHERE account = %s", (account,))
                remaining_records = cursor.fetchone()[0]
                
                if remaining_records == 0:
                    connection.commit()
                    return Data(
                        code="200", 
                        msg=f"成功删除 {affected_rows} 条压力数据", 
                        result=None
                    )
                else:
                    connection.rollback()
                    return Data(
                        code="500", 
                        msg=f"删除不完整，仍剩余 {remaining_records} 条记录", 
                        result=None
                    )
                    
            except pymysql.MySQLError as e:
                connection.rollback()
                return Data(
                    code="500", 
                    msg=f"删除压力数据时出错: {str(e)}", 
                    result=None
                )
                
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库操作异常: {str(e)}", result=None)
    finally:
        connection.close()
        #删除压力
def delete_pressure_data(account: str, cursor) -> bool:
    """删除压力表数据，返回是否成功"""
    try:
        cursor.execute("DELETE FROM pressure_data WHERE account = %s", (account,))
        return True
    except pymysql.MySQLError:
        return False
    #删除基准数值

def delete_baseline_physiological_signals(account: str, cursor)->bool:
    """删除基准数值"""
    try:
        cursor.execute("DELETE FROM baseline_physiological_signals WHERE account = %s", (account,))
        return True
    except pymysql.MySQLError:
        return False
def delete_personal_prompts(account: str, cursor)->bool:
    """删除用户个性化prompts"""
    try:
        cursor.execute("DELETE FROM user_music_prompts WHERE account = %s", (account,))
        return True
    except pymysql.MySQLError:
        return False
#删除蓝牙连接数据
def delete_device_connection_form(account: str) -> Data:
    """删除指定账户的蓝牙设备连接记录"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 1. 更可靠的用户存在检查
            cursor.execute("SELECT 1 FROM user WHERE account = %s LIMIT 1", (account,))
            if not cursor.fetchone():
                return Data(code="404", msg=f"账户 {account} 不存在", result=None)
            
            # 2. 删除设备连接记录
            try:
                # 先获取要删除的记录数（用于返回信息）
                cursor.execute("SELECT COUNT(1) FROM device_connection_history WHERE account = %s", (account,))
                record_count = cursor.fetchone()[0]
                
                if record_count > 0:
                    cursor.execute("DELETE FROM device_connection_history WHERE account = %s", (account,))
                    deleted_rows = cursor.rowcount
                    
                    # 验证删除结果
                    cursor.execute("SELECT COUNT(1) FROM device_connection_history WHERE account = %s", (account,))
                    remaining = cursor.fetchone()[0]
                    
                    if remaining == 0:
                        connection.commit()
                        return Data(
                            code="200",
                            msg=f"成功删除 {deleted_rows} 条蓝牙连接记录",
                            result={"deleted_records": deleted_rows}
                        )
                    else:
                        connection.rollback()
                        return Data(
                            code="500",
                            msg=f"删除不完整，应删除 {record_count} 条，实际删除 {deleted_rows} 条",
                            result=None
                        )
                else:
                    connection.commit()  # 没有记录也算成功
                    return Data(
                        code="200",
                        msg="该账户没有蓝牙连接记录可删除",
                        result={"deleted_records": 0}
                    )
                        
            except pymysql.MySQLError as e:
                connection.rollback()
                return Data(
                    code="500",
                    msg=f"删除蓝牙连接记录时出错: {str(e)}",
                    result=None
                )
                
    except pymysql.MySQLError as e:
        return Data(
            code="500",
            msg=f"数据库操作异常: {str(e)}",
            result=None
        )
    finally:
        connection.close()

def delete_device_connection_history(account: str, cursor) -> bool:
    """删除蓝牙连接数据，返回是否成功"""
    try:
        cursor.execute("DELETE FROM device_connection_history WHERE account = %s", (account,))
        return True
    except pymysql.MySQLError:
        return False
#注销用户
def delete_user(account: str) -> Data:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户是否存在
            cursor.execute("SELECT COUNT(1) FROM user WHERE account = %s", (account,))
            if not cursor.fetchone()[0] > 0:
                return Data(code="404", msg="用户不存在", result=None)
            
            # 删除关联数据
            pressure_deleted = delete_pressure_data(account, cursor)
            device_deleted = delete_device_connection_history(account, cursor)
            baseline_phy_signals=delete_baseline_physiological_signals(account,cursor)
            personal_prompts_deleted= delete_personal_prompts(account,cursor)
            
            # 删除用户主记录
            cursor.execute("DELETE FROM user WHERE account = %s", (account,))
            
            # 验证是否删除成功
            cursor.execute("SELECT COUNT(1) FROM user WHERE account = %s", (account,))
            if cursor.fetchone()[0] == 0:
                connection.commit()
                msg = "用户成功删除"
                if not pressure_deleted:
                    msg += " (压力数据删除失败)"
                if not device_deleted:
                    msg += " (蓝牙数据删除失败)"
                if not  baseline_phy_signals:
                    msg += " (基准数值数据删除失败)"
                if not  personal_prompts_deleted:
                    msg += "(个性化prompts删除失败)"
                return Data(code="200", msg=msg, result=None)
            
            connection.rollback()
            return Data(code="500", msg="删除失败", result=None)
                
    except pymysql.MySQLError as e:
        connection.rollback()
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None) 
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

#测量基准数值
def record_baseline_physiological_signals(account:str,Heart_rate:str,Blood_pressure :str,
skin_conductance :str,skin_temperature:str)->Data:
    connection =get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户是否存在（这里会抛出UserNotFoundError）
                cursor.execute("SELECT EXISTS(SELECT 1 FROM user WHERE account = %s)", (account,))
                user_ex=cursor.fetchone()[0]
                if  user_ex==True:
                    print("用户存在")
                    cursor.execute("SELECT EXISTS(SELECT 1 FROM baseline_physiological_signals WHERE account = %s)", (account,))
                    prompts_ex=cursor.fetchone()[0]
                    if prompts_ex==True:#检查是更新数据还是插入数据
                        sql="""update calmwave_databases.baseline_physiological_signals
                            set Heart_rate = %s,
                            Blood_pressure=%s,
                            skin_conductance =%s ,
                            skin_temperature=%s
                            where account = %s
                    """
                        cursor.execute(sql,(Heart_rate,Blood_pressure,skin_conductance,skin_temperature,account))
    
                    elif prompts_ex==False:
                        sql="""INSERT INTO baseline_physiological_signals (account, Heart_rate,Blood_pressure,
                    skin_conductance ,skin_temperature)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql,(account,Heart_rate,Blood_pressure,skin_conductance,skin_temperature)) 
                else:
                    raise UserNotFoundError(account)  

                   
        connection.commit()
        return Data(code="200", msg="基准信息测量成功", result=None)

    except pymysql.Error as e:
        connection.rollback()
        raise  # 重新抛出数据库异常
    finally:
        connection.close()
#获取基准数据
def get_baseline_physiological_signals(account:str)->Data:
    connection =get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户是否存在（这里会抛出UserNotFoundError）
                cursor.execute("SELECT EXISTS(SELECT 1 FROM user WHERE account = %s)", (account,))
                user_ex=cursor.fetchone()[0]
                if  user_ex==True:
                    sql="""SElECT * From baseline_physiological_signals where account=%s"""
                    params = [account]

                    cursor.execute(sql, params)
                    result = cursor.fetchall()
                else:
                    raise UserNotFoundError(account)

        return Data(code="200", msg="基准数据获取成功", result=result)
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
#个性化prompts调取
def get_personal_prompts(account:str)->Data: 
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM user WHERE account = %s)", (account,))
            user_ex=cursor.fetchone()[0]
            if  user_ex==True:
                # 基础 SQL 语句
                sql = """
                SELECT * FROM user_music_prompts
                WHERE account = %s 
                """
                params = [account]

                cursor.execute(sql, params)
                result = cursor.fetchall()
            else:
                raise UserNotFoundError(account)

        return Data(code="200", msg="用户prompts获取成功", result=result)
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None)
    finally:
        connection.close()
#个性化prompts存储
def store_personal_prompts(account:str,genre:str, mood:str, tempo:str,additional_requirements:str=None)->Data:
    connection =get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户是否存在（这里会抛出UserNotFoundError）
                cursor.execute("SELECT EXISTS(SELECT 1 FROM user WHERE account = %s)", (account,))
                user_ex=cursor.fetchone()[0]
                if  user_ex==True:
                    print("用户存在")
                    cursor.execute("SELECT EXISTS(SELECT 1 FROM user_music_prompts WHERE account = %s)", (account,))
                    prompts_ex=cursor.fetchone()[0]
                    if prompts_ex==True:#检查是更新数据还是插入数据 music_style emotion tempo personal_needs
                        sql="""update calmwave_databases.user_music_prompts
                            set music_style = %s,
                            emotion=%s,
                            tempo =%s ,
                            personal_needs=%s
                            where account = %s
                    """
                        cursor.execute(sql,(genre, mood, tempo , additional_requirements,account))
    
                    elif prompts_ex==False:
                        sql="""INSERT INTO user_music_prompts (account, music_style,emotion,
                    tempo ,personal_needs)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql,(account,genre, mood, tempo , additional_requirements)) 
                else:
                    raise UserNotFoundError(account)  

                   
        connection.commit()
        return Data(code="200", msg="用户个性化prompts存储成功", result=None)

    except pymysql.Error as e:
        connection.rollback()
        raise  # 重新抛出数据库异常
    finally:
        connection.close()
#查询templematin
def get_temperature(pressure_level:str, cursor)->float:
    """获得tem,返回是否成功"""
    try:
        temperature=cursor.execute("SELECT temperature FROM pressure_levels WHERE pressure_level = %s", (pressure_level,))
        return temperature
    except pymysql.MySQLError:
        return 0.0
#查询基准prompt
def get_prompt(account:str,pressure_value:str)->Data:
    connection =get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户是否存在（这里会抛出UserNotFoundError）
                temperature=get_temperature(pressure_value,cursor)
                sql="""SElECT prompts From baseline_music_prompts where pressure_level=%s"""
                params = [pressure_value]
                cursor.execute(sql,params)
                prompts=cursor.fetchall() 
              
                
                selected = random.choice(prompts)[0]  # 提取元组中的第一个元素
                sql="""SELECT CONCAT(COALESCE(music_style, ''), ',', COALESCE(emotion, ''), ',', COALESCE(tempo, ''),',',COALESCE(personal_needs, '')) AS pre_prompt From user_music_prompts where account=%s"""
                params = [account]
                cursor.execute(sql,params)
                pre_prompt=cursor.fetchall()
                pre_prompt = " ".join([prompt[0] for prompt in pre_prompt]) if pre_prompt else "" 
                out_prompts=selected+","+pre_prompt


                

        return Data(code="200", msg="基准数据获取成功", result={"out_prompts": out_prompts, "temperature": temperature})
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None)
    finally:
        connection.close()
#存储store_feedback_data
def store_feedback_data(selectedType:str,feedbackContent:str,contact: str,account: str,images: str=None):
    connection =get_db_connection()
    # 如果 images 参数为空，将其设置为一个空的 JSON 数组
    images_json = json.dumps(images) if images else json.dumps([])
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO feedback_data (selectedType,feedbackContent,contact,account,images,feedback_time)
            VALUES (%s, %s, %s,%s, %s,NOW())
            """
            cursor.execute(sql, (selectedType,feedbackContent,contact,account,images_json))
            connection.commit()
      
        return Data(code="200", msg="意见反馈表数据存储成功", result=None)
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None)
    finally:
        connection.close()
#报表获取压力
def get_day_pressure(account:str,date:str)->Data:
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 基础 SQL 语句
            sql = """
             SELECT
                HOUR(record_time) AS hour,
                IFNULL(AVG(pressure_value), 0) AS avg_pressure
            FROM
                pressure_data
            WHERE
                account = %s
                AND DATE(record_time) = %s
            GROUP BY
                hour
            ORDER BY
                hour;
            """
            params = [account, date]

            cursor.execute(sql, params)
            result = cursor.fetchall()
            print("Original result:", result)
            #return Data(code="200", msg="压力数据获取成功", result=result)
            # 补充缺失的小时数据，假设压力为0
            hourly_data = {hour: 0 for hour in range(24)}
            for row in result:
                hourly_data[row[0]] = row[1]

            # 将结果按小时顺序输出
            final_result = [{"hour": hour, "avg_pressure": hourly_data[hour]} for hour in range(24)]



        return Data(code="200", msg="压力数据获取成功", result=final_result)
    except pymysql.MySQLError as e:
        return Data(code="500", msg=f"数据库异常: {str(e)}", result=None)
    finally:
        connection.close()
    



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
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler, MinMaxScaler

xgb_model = xgb.XGBClassifier()
xgb_model.load_model("xgb_stress_model.json") 

scaler_ecg = MinMaxScaler()
scaler_eda = StandardScaler()


def preprocess_and_predict(ecg_hrv, eda_std, stress_phase):
    """
    预处理单条数据并预测压力水平
    :param ecg_hrv: 心率变异性 (float)
    :param eda_std: 皮电标准差 (float)
    :param stress_phase: 压力测试阶段 (int)
    :return: 预测的压力等级 (int)
    """
    # 处理 ECG_HRV（取对数）
    ecg_hrv = np.log(ecg_hrv + 1)

    # 归一化 & 标准化
    ecg_hrv = scaler_ecg.fit_transform(np.array([[ecg_hrv]]))[0][0]
    eda_std = scaler_eda.fit_transform(np.array([[eda_std]]))[0][0]

    # 生成新特征
    ecg_eda_interaction = ecg_hrv * eda_std
    ecg_squared = ecg_hrv ** 2

    # 创建特征向量
    feature_vector = np.array([[ecg_hrv, eda_std, ecg_eda_interaction, ecg_squared, stress_phase]])

    # 进行预测
    predicted_stress_level = xgb_model.predict(feature_vector)[0]+1

    return predicted_stress_level


# if __name__ == "__main__":
#     # 用户输入
#     ecg_hrv = float(input("请输入 ECG_HRV（心率变异性）: "))
#     eda_std = float(input("请输入 EDA_STD（皮电标准差）: "))
#     stress_phase = int(input("请输入 Stress_Test_Phase（压力测试阶段）: "))
#
#     # 预测压力水平
#     predicted_level = preprocess_and_predict(ecg_hrv, eda_std, stress_phase)
#
#     # 输出结果
#     print(f"预测的压力等级: {predicted_level}")

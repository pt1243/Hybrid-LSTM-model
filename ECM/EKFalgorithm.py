import numpy as np
import pandas as pd
import scipy as s
import matplotlib.pyplot as plt


def EKF(r, p, q, battery_num):
    # load actual data from file
    bat = []
    bat.append(pd.read_csv('data/' + battery_num + '_TTD.csv'))
    bat = pd.concat(bat)
    current = bat['Current_measured']
    temperature = bat['Temperature_measured']
    Vt_act = bat['Voltage_measured']

    # Load soc ocv data
    dat = []
    dat.append(pd.read_excel('ECM/SOC_OCV_data.xlsx'))
    dat = pd.concat(dat)
    soc_dat = dat['SOC']
    ocv_dat = dat['OCV']

    # Load interpolant data
    interpolants = []
    interpolants.append(pd.read_excel('ECM/battery_model.xlsx'))
    interpolants = pd.concat(interpolants)
    SOC_dat = interpolants['SOC']
    R0_dat = interpolants['R0']
    R1_dat = interpolants['R1']
    R2_dat = interpolants['R2']
    C1_dat = interpolants['C1']
    C2_dat = interpolants['C2']
    T_dat = interpolants['T']

    # Load current and temperature data
    soc_init = 1
    X = np.matrix([[soc_init], [0], [0]])
    deltaT = 1
    Qn_rated = 2.3*3600

    sococv = np.polyfit(soc_dat, ocv_dat, 9)
    sococv = np.poly1d(sococv)
    dsococv = np.polyder(sococv)

    # State space model
    R_x = r
    P_x = np.matrix([[p, 0, 0], [0, p, 0], [0, 0, p]])
    Q_x = np.matrix([[q, 0, 0], [0, q, 0], [0, 0, q]])

    SOC_est = []
    Vt_est = []
    Vt_err = []
    ik = len(current)

    # EKF
    for k in range(ik):
        T_val = temperature[k]
        U = current[k]
        soc = X.item(0)
        V1 = X[1]
        V2 = X[2]

        R0 = s.interpolate.griddata((SOC_dat, T_dat), R0_dat, (soc, T_val), method='nearest')
        R1 = s.interpolate.griddata((SOC_dat, T_dat), R1_dat, (soc, T_val), method='nearest')
        R2 = s.interpolate.griddata((SOC_dat, T_dat), R2_dat, (soc, T_val), method='nearest')
        C1 = s.interpolate.griddata((SOC_dat, T_dat), C1_dat, (soc, T_val), method='nearest')
        C2 = s.interpolate.griddata((SOC_dat, T_dat), C2_dat, (soc, T_val), method='nearest')

        ocv_pred = sococv(np.array(soc))

        tau1 = R1*C1
        tau2 = R2*C2

        a1 = np.exp(-deltaT/tau1).item(0)
        a2 = np.exp(-deltaT/tau2).item(0)

        b1 = (R1 * (1-a1)).item(0)
        b2 = (R2 * (1-a2)).item(0)

        terminal_voltage = ocv_pred - R0 * U - V1 - V2 

        dOCV = dsococv(soc)

        C_x = np.matrix([dOCV, -1, -1])

        Error_x = Vt_act[k] - terminal_voltage

        Vt_est.append(terminal_voltage.item(0))
        Vt_err.append(Error_x.item(0))
        SOC_est.append(soc)

        # Prediction
        A = np.matrix([[1, 0, 0], [0, a1, 0], [0, 0, a2]])
        B = np.matrix([[(-deltaT/Qn_rated)], [b1], [b2]])
        X = A*X + B*U
        P_x = A*P_x*A.T + Q_x
        Kalman_gain = P_x*C_x.T*(C_x*P_x*C_x.T + R_x).I
        X = X + Kalman_gain*Error_x
        P_x = (np.eye(3) - Kalman_gain*C_x)*P_x

    total_err = (np.sum(np.square(Vt_err)))/len(Vt_err)
    print(f'MSE is {total_err}')
    return SOC_est, Vt_est, Vt_err, Vt_act, total_err


# testing if the algorithm works
# please uncomment this if you want to run the optimiser
soc_est, vt_est, vt_err, vt_act, total_err = EKF(0.03, 0.0032354, 0.012911, 'B0005')  # best hyperparams from GA after 10 gen w/ popsize == 10
plt.plot(vt_est, label='Estimated Voltage')
plt.plot(vt_act, label='Actual Voltage')
plt.legend()
plt.show()

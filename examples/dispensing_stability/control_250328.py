# ---------------------------------------------------------------------------
# PROVENANCE — HISTORICAL SCRIPT, NOT RUNNABLE IN THIS REPOSITORY
#
# This is the control script that was actually executed on 2025-03-28 on the
# laboratory control PC to produce `weight.csv` in this directory: 100 repeated
# injections of a nominal 3 mL of ion-exchanged water, each followed by a
# reading of the electronic balance.
#
# It is reproduced here verbatim (apart from this header and the Bluetooth MAC
# addresses and pipette serial numbers, which were replaced by placeholders) for
# provenance only.
# It depends on three lab-local modules that are NOT part of this repository
# and are not published:
#
#   * `ika_control`       — serial driver for the IKA RET control-visc stirrer
#   * `material_injection`— the Dobot + Picus 2 aspirate/dispense sequence
#   * `BCE8221`           — serial driver for the Sartorius BCE822i balance
#
# It also hard-codes COM ports and a Bluetooth address of the original setup.
# The equivalent functionality in this repository is provided by
# `src/devices/` (dobot, picus2, scale) and `src/flow/`; write a JSON flow and
# run it with `python -m src.flow.run_flow` instead of running this file.
#
# Do not expect `python control_250328.py` to work here — it will fail at the
# imports below. Comment blocks inside `main()` are as they were on the day of
# the measurement (stirrer / second-robot steps disabled for this run).
# ---------------------------------------------------------------------------

import time
import pandas as pd

import ika_control
import material_injection
import BCE8221

def main():

    # ika_temperature = 20
    # ika_speed_1 = 600
    # ika_speed_2 = 200
    # heating_time = 10

    aspiration_amount_1 = 3
    dispensation_speed_1 = 9
    wait_seconds = 1
    # aspiration_amount_2 = 4
    # dispensation_speed_2 = 1
    #
    # # RET control-visc オブジェクトの作成
    # ika_port_name_1 = 'COM17'
    # ika_port_name_2 = 'COM16'
    #
    # ika_device_1 = ika_control.RETControlVisc(port=ika_port_name_1)
    # ika_device_2 = ika_control.RETControlVisc(port=ika_port_name_2)
    # ika_device_1.send_command(f'START_1')
    # time.sleep(1)
    # ika_device_1.send_command(f'START_90')
    #
    # ika_device_1.start_stirring(ika_device_1, ika_temperature, ika_speed_1)
    # ika_device_2.start_stirring(ika_device_2, ika_temperature, ika_speed_1)
    # time.sleep(heating_time)
    # ika_device_1.start_stirring(ika_device_1, ika_temperature, ika_speed_2)
    # ika_device_2.start_stirring(ika_device_2, ika_temperature, ika_speed_2)

    BCE8221_port = 'COM4'
    balance = BCE8221.SerialBalance(port=BCE8221_port)  # インスタンス作成

    list_weight = []
    last_weight = balance.get_weight()  # 重量データ取得

    for i in range(100):

        mi_params = {
            "picus2_address": 'XX:XX:XX:XX:XX:XX',  # pipette 1
            "picus2_debug": False,
            "dobot_port_name": "COM7",
            "homing": False,
            "initial_position": [0, 200, 150],
            "xy_offset_aspirate": [0, 0, 0],
            "amount": aspiration_amount_1,
            "max_amount_each": 10,
            "aspiration_angle": 90,
            "dispensation_angle": 0,
            "aspiration_speed": 9,
            "dispensation_speed": dispensation_speed_1,
            "z_offset_aspirate": -160,
            "z_offset_dispense": -100,
            "wait_seconds": wait_seconds,
        }

        material_injection.main(mi_params)

        weight_now = balance.get_weight()  # 重量データ取得
        print(i, f"抽出された数値: {weight_now}")

        weight = round(weight_now - last_weight, 2)
        last_weight = weight_now

        list_weight.append(weight)

        # DataFrameに変換（列名を 'weight' として指定）
        df = pd.DataFrame(list_weight, columns=['weight'])

        # CSVファイルとして保存（例: weight.csv）
        df.to_csv('weight.csv', index=False)


    balance.close()  # 通信終了

    print(list_weight)

    # time.sleep(3)
    #
    # mi_params = {
    #     "picus2_address": 'XX:XX:XX:XX:XX:XX',  # pipette 2
    #     "picus2_debug": False,
    #     "dobot_port_name": "COM14",
    #     "homing": False,
    #     "initial_position": [0, -250, 150],
    #     "amount": aspiration_amount_2,
    #     "max_amount_each": 10,
    #     "aspiration_angle": -90,
    #     "dispensation_angle": 0,
    #     "aspiration_speed": 9,
    #     "dispensation_speed": dispensation_speed_2,
    #     "z_offset_aspirate": -20,
    #     "z_offset_dispense": -100,
    # }
    #
    # material_injection.main(mi_params)
    #
    # ika_device_1.stop_stirring(ika_device_1)
    # ika_device_1.stop_stirring(ika_device_2)
    #
    # for i in range(10):
    #     status = ika_device_1.send_command(f'STATUS_90')
    #     print(status)
    #     if str(status).strip() == '1041 90':
    #         print(ika_device_1.send_command('IN_PV_90'))
    #         break
    #     else:
    #         time.sleep(1)
    #
    # ika_device_1.send_command(f'STOP_1')
    # ika_device_1.send_command(f'STOP_90')
    # # ika_device.reset_device()
    #
    # ika_device_1.close()
    # ika_device_2.close()


if __name__ == '__main__':
    main()
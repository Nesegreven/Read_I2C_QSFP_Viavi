import viavi
import time

a=viavi.Mpa2100()
a.connect('10.10.40.197')
a.show_running_applications()

a.select_application("TermEth100GL2Traffic_101")
#a.select_application("TermEth40GL2Traffic_102")

a.remote_session_start()

data_file=open("data.txt", "w")

data_file.write("Rx_power" + "," + "time_elapsed" + "," + "err seconds")
time_seconds = a.test_time()

print(type(a.error_present()))

while int(a.error_present()) < 2:
    data_file.write(a.read_Rx_power() + ",")
    data_file.write(a.test_time() + ",")
    data_file.write(a.error_present() + "\n")
    print(a.test_time() + "  ,  " + a.read_Rx_power())
    time.sleep(5)


data_file.close()
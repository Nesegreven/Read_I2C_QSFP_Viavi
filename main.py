import viavi
import time

a=viavi.Mpa2100()
a.connect('10.10.10.20')
#a.connect('10.10.50.150')
a.show_running_applications()

#a.select_application("TermEth100GL2Traffic_101")
a.select_application("TermEth100GL2Traffic_101")

a.remote_session_start()


for i in range(10):
    a.read_pre_fec_ber_INPHI()
    #a.read_pre_fec_ber_Eopto()
    time.sleep(0.5)


a.gui()
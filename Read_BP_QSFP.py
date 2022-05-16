import viavi
import time as t

a=viavi.Mpa2100()
a.connect('10.10.40.197')

a.launch_system_application("TermEth40GL2Traffic 1")


#a.select_application("TermEth100GL2Traffic_101")
a.select_application("TermEth40GL2Traffic_101")

a.remote_session_start()



page="BasePage"


a.i2c_read_page_qsfp(page)
print("\n")

#a.i2c_read_page_qsfp(32)


#a.select_application("TermEth100GL2Traffic_102")
#a.remote_session_start()

#print('100G' + "\n")

#a.i2c_read_page_qsfp('BasePage')
#print("\n")

#a.i2c_read_page_qsfp(0)


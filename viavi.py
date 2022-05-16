"""
========================================================================================================================
# Information
# SCPI for VIAVI does not have an prompt (e.g. tn.read_until(b"prompt") is not possible).
Set an value "****$$$$" that will not be matched, interrupted at timeout instead.
========================================================================================================================
"""

# TODO clean up: <FUNCTION (traffic)> <ADDITIONAL INFO> < STATE(start/stop/toggle)>  --> (traffic_FC_start, laser_on)

import inspect
import re
import telnetlib
import time


class Mpa2100:
    """Class for Instrument Mpa2100 (viavi)"""

    # SCPI Commands
    SCPI_multiple_cmd_separator = " ;"
    SCPI_cmd_sys_error = ":SYSTem:ERRor?"
    SCPI_cmd_rem_visible = "*REM VISIBLE FULL"  # Remote Operational Mode – VISIBLE
    SCPI_cmd_app_cap = ":SYST:APPL:CAPP?"  # View possible applications

    SCPI_cmd_error_seconds = ":SENSe:DATA? ESECOND:PERFORMANCE:Ethernet:G826:NE:OOS"
    SCPI_cmd_time_elapsed = ":SENSe:DATA? SECOND:TEST:ELAPSED"

    SCPI_cmd_select_app = (
        ":SYSTem:APPLication:SELect"
    )  # e.g. :SYSTem:APPLication:SELect TermEth10GL2Traffic_101
    SCPI_cmd_create_new_session = ":SESSion:CREate"
    SCPI_cmd_start_session = ":SESSion:STARt"
    SCPI_cmd_event_log_100G_appl = (
        ":sense:data? STRING:TEST:EVENT:LOG"
    )  # Working for the 100G application
    SCPI_cmd_exit_app = ":EXIT"
    SCPI_cmd_end_session = ":SESS:END"
    SCPI_cmd_read_tx_QSFP = ":sense:data? FLOAT:PHYSICAL:QSFP:TX:POWER:LEVEL:SUM"
    SCPI_cmd_read_rx_QSFP = ":sense:data? FLOAT:PHYSICAL:QSFP:RX:POWER:LEVEL:SUM"
    SCPI_cmd_read_tx_SFP = ":sense:data? INTEGER:PHYSICAL:TX:LEVEL:DBM"
    SCPI_cmd_sfp1_present = ":sense:data? CSTATUS:PHYSICAL:SFP1:PRESENT"
    SCPI_cmd_overload = ":SENSe:DATA? CSTatus:PHYSical:OVRLd"
    # SCPI_cmd_reset_overload_sfp1 = ':INPut:SFP1:OVERload:OPTic:RESet' # OLD, comply to sw???
    # SCPI_cmd_reset_overload_sfp2 = ':INPut:SFP2:OVERload:OPTic:RESet' # OLD, comply to sw???
    SCPI_cmd_reset_overload_sfp1 = ":INPUT:SFP1:OVERLOAD:OPTIC:RESET"  # ok for 27.1.0
    SCPI_cmd_reset_overload_sfp2 = (
        ":INPUT:SFP1:OVERLOAD:OPTIC:RESET"
    )  # ok for 27.1.0 # Note!working for port2

    SCPI_cmd_link_status = ":SENSE:DATA? CSTATUS:PCS:PHY:LINK:ACTIVE"
    SCPI_cmd_toggle_laser = ":OUTPUT:OPTIC"
    SCPI_cmd_laser_status = ":OUTPUT:OPTIC?"
    SCPI_cmd_launch_app = (
        ":SYSTem:APPLication:LAUNch"
    )  # e.g.: :SYSTem:APPLication:LAUNch TermEth1GL2Traffic 2
    SCPI_cmd_verify_app_launched = ":SYST:APPL:LAUN?"
    SCPI_cmd_toggle_traffic = ":SOURCE:MAC:TRAFFIC"  # Unique for "Eth". Start/stop traffic
    SCPI_cmd_toggle_traffic_fchannel = (
        ":SOURCE:FCHANNEL:TRAFFIC"
    )  # Unique for "FC". Start/stop traffic
    SCPI_cmd_read_traffic_button_status = (
        ":SOURCE:MAC:TRAFFIC?"
    )  # Unique for "Eth". Read if start/stop.
    SCPI_cmd_read_traffic_fchannel_button_status = (
        ":SOURCE:FCHANNEL:TRAFFIC?"
    )  # Unique for "FC". Read if start/stop -traffic,
    SCPI_cmd_reset_stop_test = ":ABORt"  # Test stop
    SCPI_cmd_reset_start_test = ":INITiate"  # Test start
    SCPI_cmd_insert_single_code_error = (
        ":SOURCE:PCS:PHY:INSERT:CODE"
    )  # Insert single code 'Error' (at Eth)

    # Interrupt reading when the following sub-strings are matched
    read_until_error_free = b"No error"
    read_until_timeout = b"***$$$---@@@+++"

    def __init__(self, port=8000, timeout=30):
        self.eqpt_ber_ip = '10.10.40.197'
        self.port = port
        self.timeout = timeout

    @staticmethod
    def __error_codes():
        """return a list of known error codes for SCPI"""
        error_codes = [
            "-100",
            "-102",
            "-103",
            "-108",
            "-109",
            "-113",
            "-120",
            "-121",
            "-138",
            "-141",
            "-144",
            "-150",
            "-151",
            "-200",
            "-220",
            "-221",
            "-222",
            "-224",
            "-231",
        ]
        return error_codes

    def __test_status(self, status, function_name, cmd=None):
        """
        :param status: Includes VIAVI error codes if an "pass" or "fail"
        :return:
        """
        # if "No error" in status:  # debug
        if "Error Code" in status:
            # e.g.: error --> 'Error Code: "-200, "Execution error"'
            status = status.replace("\n", "")
            Logger_simple().log(func=function_name, cmd=cmd, msg=f"{repr(status)}")

        # second check sometimes does the error check not working. an reply can look like:
        # "\n-113, "Undefined header; could not find"
        error_codes = self.__error_codes()
        for error_code in error_codes:
            if error_code in status:
                status = status.replace("\n", "")
                Logger_simple().log(func=function_name, cmd=cmd, msg=f"{repr(status)}")

    # TODO fix - log fd
    #  Telnet.fileno()¶Return the file descriptor of the socket object used internally.
    #  https://docs.python.org/3.7/library/telnetlib.html

    def connect(self, ip):
        """Connect to SCPI instrument"""
        #host = self.eqpt_ber_ip
        host=ip
        port = self.port

        # Telnet no.1 - Get Second Port
        tn = telnetlib.Telnet(host, port, self.timeout)
        command = "*REM".encode("ascii") + b"\n"
        tn.write(command)  # Remote Operational Mode
        command = 'MOD:FUNC:PORT? BOTH, BASE, "BERT"'.encode("ascii") + b"\n"
        tn.write(command)  # Query for the module's port number – MOD
        second_port = tn.read_until(b"****$$$$", timeout=2).decode("ascii").rstrip("\n")  # Result
        tn.close()

        # Telnet no.2 - Get Third Port
        port = second_port  # Second port, e.g. "800x"
        tn = telnetlib.Telnet(host, port, self.timeout)
        command = "*REM".encode("ascii") + b"\n"
        tn.write(command)  # Remote Operational Mode
        command = ':SYST:FUNC:PORT? BOTH,BASE,"BERT"'.encode("ascii") + b"\n"
        tn.write(command)  # Query for the module's port number – SYST
        third_port = tn.read_until(b"****$$$$", timeout=2).decode("ascii").rstrip("\n")  # Result
        tn.close()

        # Telnet no.3 - Get the actual port
        port = third_port  # Third port, e.g. "800x"
        tn = telnetlib.Telnet(host, port, self.timeout)
        command = "*REM".encode("ascii") + b"\n"
        tn.write(command)  # Remote Operational Mode
        self.tn = tn


    def remote_operational_mode(self):
        """Set remote operational mode"""
        command = (
            self.SCPI_cmd_rem_visible + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    def select_running_config(self, port):
        # Get running config
        # *** Call show running config insted...!!!
        command = self.SCPI_cmd_app_cap + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        self.tn.write(command.encode("ascii") + b"\n")
        applications_running = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(applications_running, inspect.currentframe().f_code.co_name)

        # Extract the config based on selected port
        pattern = r"\w+_10" + str(port)
        application = re.findall(pattern, applications_running)
        if application:
            application = application[0]

        # Select application
        command = (
            self.SCPI_cmd_select_app
            + " "
            + application
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    def remote_session_start(self):
        """Start a remote session on instrument"""
        command = (
            self.SCPI_cmd_create_new_session
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)


    def event_log(self, log=False):
        """ return: dictionary, key's: status, status_log, status_bool, event_log"""
        # Note! after the laser is turned on, DUT (e.g. 1610) system is generating an transient (time to time)
        # and viavi is moved in to the "overload mode" and requires an respond.
        command = (
            self.SCPI_cmd_event_log_100G_appl
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        event_log = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(event_log, inspect.currentframe().f_code.co_name)

        helper_status = Status()

        # test
        if "result" not in event_log:
            status_dict = helper_status.get_status_dict(return_passed_dict=True)
        else:
            status_dict = helper_status.get_status_dict(return_failed_dict=True)

        # append event log to status dict
        status_dict.update({"event_log": event_log})

        Logger_simple().log_raw_data(log=log, raw_data_to_log=f"{repr(event_log)}")
        return status_dict

    def overload(self):
        # force the overload state: - toggle "laser on" sleep 0.5s "laser on" (10-20times). setup: 1610, sfp: 1310.
        # Result = 1 --> overload (overload --> result: "\n1\n0, "No error" no overload --> result: "\n0\n0, "No error")
        # At the moment viavi is not supporting to disable the overload function (not very convenient)
        command = (
            self.SCPI_cmd_overload + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        return status

    def overload_reset_sfp1(self):
        command = (
            self.SCPI_cmd_reset_overload_sfp1
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        reset_overload_sfp1 = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(reset_overload_sfp1, inspect.currentframe().f_code.co_name)
        time.sleep(60)

    def overload_reset_sfp2(self):
        command = (
            self.SCPI_cmd_reset_overload_sfp2
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        reset_overload_sfp2 = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        Logger_simple().log_raw_data(
            raw_data_to_log=f"temp1111111, reset_overload_sfp2: {repr(reset_overload_sfp2)}"
        )
        self.__test_status(reset_overload_sfp2, inspect.currentframe().f_code.co_name)
        time.sleep(60)

    # TODO function "overload_reset_sfp" is not working... (quick fix move back to privious solution overload_reset_sfp1, overload_reset_sfp2)
    def overload_reset_sfp(self, port=None):
        if port == 1:
            SCPI_cmd_reset_overload_sfp = self.SCPI_cmd_reset_overload_sfp1
        elif port == 2:
            SCPI_cmd_reset_overload_sfp = self.SCPI_cmd_reset_overload_sfp2
        else:
            raise AttributeError(f"Expected port 1 or 2, got {port}!")
        command = (
            self.SCPI_cmd_reset_overload_sfp
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        reset_overload_sfp = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        Logger_simple().log_raw_data(
            raw_data_to_log=f"temp1111111, reset_overload_sfp{port}: {repr(reset_overload_sfp)}"
        )
        self.__test_status(reset_overload_sfp, inspect.currentframe().f_code.co_name)
        time.sleep(60)

    def show_running_applications(self):
        """return a list, e.g.: TermEth100GL2Traffic_101, TermEth100GL2Traffic_102"""
        command = self.SCPI_cmd_app_cap + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        self.tn.write(command.encode("ascii") + b"\n")
        result = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        #self.__test_status(result, inspect.currentframe().f_code.co_name)

        # extract
        result_list = []
        port1 = re.findall(r"\w+_101", result)
        if port1:
            result_list.append(port1[0])
        port2 = re.findall(r"\w+_102", result)
        if port2:
            result_list.append(port2[0])

        return result_list

    def close_running_application(self, application):
        """Select application - Depending on input parameters port and application
        :param port_no: Input form is 1 or 2
        :param application: Input form e.g. "TermEth10GL2Traffic"
        :return: none
        """
        # TODO: Function works but it I get an error code -200 "Execution error" when closing "TermEth40GL2Traffic"
        command = (
            self.SCPI_cmd_select_app
            + " "
            + application
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

        # Toggle the laser - assume it's turned on...
        command = (
            self.SCPI_cmd_toggle_laser + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        toggle_laser = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(toggle_laser, inspect.currentframe().f_code.co_name)

        # Close the application
        command = (
            self.SCPI_cmd_exit_app + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

        # TODO Replace the sleep below with some better function, waiting for a solution from Viavi (2019-12-20).
        time.sleep(60)  # Sleep util the application is closed -

    def launch_system_application(self, application):
        """Launch system application on port"""
        # Launch application.
        command = (
            self.SCPI_cmd_launch_app
            + " "
            + application
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )

        self.tn.read_until(b"test", timeout=1)

        self.tn.write(command.encode("ascii") + b"\n")

        self.tn.read_until(b"test", timeout= 1)

        #status = (
        #    self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        #)
        #self.__test_status(status, inspect.currentframe().f_code.co_name)

        # Verify "in time" when the application is launched.
        #command = (
        #    self.SCPI_cmd_verify_app_launched
        #    + self.SCPI_multiple_cmd_separator
        #    + self.SCPI_cmd_sys_error
        #)
        #self.tn.write(command.encode("ascii") + b"\n")
        #status = self.tn.read_until(b"_10", timeout=60).decode("ascii").rstrip("\n")
        #self.__test_status(status, inspect.currentframe().f_code.co_name)

    def select_application(self, application):
        """Select application on port
        :param port_no: Input form is 1 or 2
        :param application: Input form e.g. "TermEth10GL2Traffic"
        """
        # Select application - Depending on input parameters port and application
        command = (
            self.SCPI_cmd_select_app
            + " "
            + application
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)


    def read_tx_power(self, trx_type=None):
        """Read tx power for qsfp or sfp"""
        if trx_type == "qsfp":
            tx_pow_str = self.SCPI_cmd_read_tx_QSFP
        elif trx_type == "sfp":
            tx_pow_str = self.SCPI_cmd_read_tx_SFP
        else:
            raise AttributeError(f"Expected 'sfp' or 'qsfp' transceiver type, got '{trx_type}'")
        command = tx_pow_str + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        self.tn.write(command.encode("ascii") + b"\n")
        tx_power = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(tx_power, inspect.currentframe().f_code.co_name)

    def sfp1_present(self):
        print(
            'Note, :sense:data? CSTATUS:PHYSICAL:SFP2:PRESENT is not avaleble!!!! I had an return of "1", verify with SFP at slot 2 --> what return???'
        )
        command = (
            self.SCPI_cmd_sfp1_present + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        qsfp_tx_power = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(qsfp_tx_power, inspect.currentframe().f_code.co_name)

    def insert_single_code_error(self):
        """Insert single code 'Error' (at Eth)"""
        command = (
            self.SCPI_cmd_insert_single_code_error
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    # Laser (on/off)
    def laser_on(self):
        """Turn laser on"""
        # Note! after the laser is turned on, DUT (e.g. 1610) system is generating an transient (time to time).
        # Use overload (SFP or QSFP) function to handle the transient.
        status = self.laser_status()
        if "OFF" in status:
            self.laser_toggle()

    def laser_off(self):
        """Turn laser off"""
        status = self.laser_status()
        if "ON" in status:
            self.laser_toggle()

    def laser_status(self):
        """Check laser status"""
        command = (
            self.SCPI_cmd_laser_status + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        return status

    def laser_toggle(self):
        """Toggle laser status"""
        command = (
            self.SCPI_cmd_toggle_laser + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    def link_status(self):
        """
        info. when link: \n1\n0 (waiting for link: \n0\n0, fail state: \n9.91e+37\n0)
        note! it's not working for TermEth100GL2Traffic! (working for TermEth10GL2Traffic) sw: 27.1.0
        """
        # TODO fix an solution for TermEth100GL2Traffic, bug? upg inst?
        # TODO test for other formats FC etc.
        command = (
            self.SCPI_cmd_link_status + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        Logger_simple().log(msg=f"*** {repr(status)}")
        Logger_simple().log(msg=f"*** {status}")
        if "\n1\n" in status:
            status_bool = True
        else:
            status_bool = False

        return status_bool

    # traffic - FC (start/stop)
    def traffic_fc_start(self):
        """Start fc traffic"""
        status = self.traffic_fc_status()
        print("status", status)
        if "OFF" in status:
            self.traffic_fc_toggle()

    def traffic_fc_stop(self):
        """Stop fc traffic"""
        status = self.traffic_fc_status()
        print("status", status)
        if "ON" in status:
            self.traffic_fc_toggle()

    def traffic_fc_status(self):
        """Check fc traffic status"""
        command = (
            self.SCPI_cmd_read_traffic_fchannel_button_status
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        return status  # 'ON' or 'OFF'

    def traffic_fc_toggle(self):
        """Toggle fc traffic status"""
        command = (
            self.SCPI_cmd_toggle_traffic_fchannel
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    # traffic - Eth, SDH (start/stop)
    def traffic_mac_start(self):
        # Note! after the laser is turned on, DUT (e.g. 1610) system is generating an transient (time to time)
        # and viavi is moved in to the "overload mode" and requires an respond.
        status = self.traffic_mac_status()
        if "OFF" in status:
            self.traffic_mac_toggle()

    def traffic_mac_stop(self):
        status = self.traffic_mac_status()
        if "ON" in status:
            self.traffic_mac_toggle()

    def traffic_mac_status(self):
        command = (
            self.SCPI_cmd_read_traffic_button_status
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        return status  # 'ON' or 'OFF'

    def traffic_mac_toggle(self):
        command = (
            self.SCPI_cmd_toggle_traffic
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    # test (start, stop and restart the test)
    def test_restart(self):
        # include "test_stop" and "test_start")
        # Info.:If the laser just enabled, it requires approx: 2-15s before the link is up and the restart is available
        self.test_stop()
        self.test_start()

    def test_stop(self):
        # corresponds to the "start/stop test button" at the GUI (no toggle, use different commands, e.g :ABORt)
        command = (
            self.SCPI_cmd_reset_stop_test
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        command = command.encode("ascii") + b"\n"
        self.tn.write(command)
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    def test_start(self):
        # corresponds to the "start/stop test button" at the GUI (no toggle, use different commands, e.g. :INITiate).
        command = (
            self.SCPI_cmd_reset_start_test
            + self.SCPI_multiple_cmd_separator
            + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        time.sleep(1)  # wait until the laser is up running (before other actions)

    # *** To be replaced...
    def restart(self):  # Restart Button
        self.test_restart()
        """
        # include "stop test" and "start test")
        # Note! after the laser is turned on, DUT (e.g. 1610) system is generating an transient (time to time)
        # and viavi is moved in to the "overload mode" and requires an respond.
        command = self.SCPI_cmd_reset_stop_test + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        command = command.encode('ascii') + b"\n"
        self.tn.write(command)
        status = self.tn.read_until(self.read_until_error_free, timeout=2).decode('ascii').rstrip('\n')
        self.__test_status(status, inspect.currentframe().f_code.co_name)

        command = self.SCPI_cmd_reset_start_test + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        self.tn.write(command.encode('ascii') + b"\n")
        status = self.tn.read_until(self.read_until_error_free, timeout=2).decode('ascii').rstrip('\n')
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        time.sleep(1)  # wait until the laser is up running (before other actions)
        """

    def reboot(self):
        """
        tn = self.tn
        command = ':SYSTem:REBoot' + b"\n"
        tn.write(command)
        status = self.tn.read_until(self.read_until_error_free, timeout=5).decode('ascii').rstrip('\n')
        self.__test_status(status, inspect.currentframe().f_code.co_name)
        """
        tn = self.tn
        command = ":SYSTem:REBoot"

        self.tn.write(command.encode("ascii") + b"\n")

        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        self.__test_status(status, inspect.currentframe().f_code.co_name)

    def remote_session_end(self):
        command = (
            self.SCPI_cmd_end_session + self.SCPI_multiple_cmd_separator + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        status = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        #self.__test_status(status, inspect.currentframe().f_code.co_name)

    def close(self):
        self.tn.close()

    def select40G_P2(self):
        command = (
            ':SYSTem:APPLication:SELect TermEth40GL2Traffic_102'
        )
        self.tn.write(command.encode("ascii") + b"\n")

        result = (
            self.tn.read_until(self.read_until_error_free, timeout=5).decode("ascii").rstrip("\n")
        )
        return result

    def read_i2c(self, page, address):

        page= str(page)

        command = (
                ':SENSE:EXPERT:I2C:PEEK:PAGESEL ' + page
        )
        self.tn.write(command.encode("ascii") + b"\n")
        address=str(address)
        command = (
                ':SENSE:EXPERT:I2C:PEEK:REGADDR ' + address
                + self.SCPI_multiple_cmd_separator
                + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")
        command = (
                ':SENSE:EXPERT:I2C:PEEK:Trigger'
                + self.SCPI_multiple_cmd_separator
                + self.SCPI_cmd_sys_error
        )
        self.tn.write(command.encode("ascii") + b"\n")

        command = (
            ':SENSe:DATA? :SENSE:EXPERT:I2C:PEEK:REGDATA'
        )

        self.tn.read_until(b"test",timeout=1).decode("ascii").rstrip("\n")

        self.tn.write(command.encode("ascii") + b"\n")
        result_str = self.tn.read_until(b"test", timeout=1).decode("ascii").rstrip("\n")
        print(result_str)

        result_int = int(result_str)
        result_hex = hex(result_int).lstrip("0x")

        if len(result_hex) == 0:
            result_hex = '00'
        elif len(result_hex) == 1:
            result_hex = '0' + result_hex
        else:
            result_hex = result_hex

        return result_hex


    def i2c_read_page_qsfp(self, page):

        if page == "BasePage":
            print('Base page: ')
            page=0

            col = 0
            s = "00: "
            row = 0
            print("    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F")

            for i in range(128):
                col = col + 1
                s = s + self.read_i2c(page, i) + " "
                if col == 16:
                    print((s))
                    col = 0
                    row = row + 1
                    if row == 10:
                        s = "A0" + ": "
                    elif row == 11:
                        s = "B0" + ": "
                    elif row == 12:
                        s = "C0" + ": "
                    elif row == 13:
                        s = "D0" + ": "
                    elif row == 14:
                        s = "E0" + ": "
                    elif row == 15:
                        s = "F0" + ": "
                    else:
                        s = str(row) + "0: "
        else:
            print("Page " + str(page) + ":")
            col = 0
            s = "80: "
            row = 8
            print("    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F")

            for i in range(128):
                col = col + 1
                s = s + self.read_i2c(page, 128 + i) + " "
                if col == 16:
                    print((s))
                    col = 0
                    row = row + 1
                    if row == 10:
                        s = "A0" + ": "
                    elif row == 11:
                        s = "B0" + ": "
                    elif row == 12:
                        s = "C0" + ": "
                    elif row == 13:
                        s = "D0" + ": "
                    elif row == 14:
                        s = "E0" + ": "
                    elif row == 15:
                        s = "F0" + ": "
                    else:
                        s = str(row) + "0: "

    def read_pre_fec_ber_INPHI(self):
        byte_164 = self.read_i2c(32, 182)
        byte_165 = self.read_i2c(32, 183)


        # Code to convert hex to binary
        res = "{0:016b}".format(int(byte_164 + byte_165, 16))


        #exponent = res[:5]
        #mantissa = res[5:]

        # From string in binary to decimal

        sumExponent = 0
        sumMantissa = 0

        for i in range(16):
            if i < 5:
                sumExponent = int(res[i]) * 2 ** (4 - i) + sumExponent
            if i >= 5:
                sumMantissa = int(res[i]) * 2 ** (15 - i) + sumMantissa

        if sumMantissa >= 1000:
            print(str(sumMantissa / 1000), "E", str(sumExponent - 21))
        else:
            print(str(sumMantissa), "E", str(sumExponent - 24))

    def read_pre_fec_ber_Eopto(self):
        byte_158 = self.read_i2c(32, 158)
        byte_159 = self.read_i2c(32, 159)


        # Code to convert hex to binary
        res = "{0:016b}".format(int(byte_158 + byte_159, 16))


        #exponent = res[:5]
        #mantissa = res[5:]

        # From string in binary to decimal

        sumExponent = 0
        sumMantissa = 0

        for i in range(16):
            if i < 5:
                sumExponent = int(res[i]) * 2 ** (4 - i) + sumExponent
            if i >= 5:
                sumMantissa = int(res[i]) * 2 ** (15 - i) + sumMantissa

        if sumMantissa >= 1000:
            print(str(sumMantissa / 1000), "E", str(sumExponent - 21))
        else:
            print(str(sumMantissa), "E", str(sumExponent - 24))

    def read_Rx_power(self):
        command=self.SCPI_cmd_read_rx_QSFP

        # Empty buffert
        self.tn.read_until(b"hello", timeout=0.5).decode("ascii").rstrip("\n")

        self.tn.write(command.encode("ascii") + b"\n")
        result_str = self.tn.read_until(b"test", timeout=0.5).decode("ascii").rstrip("\n")
        return result_str

    def error_present(self):
        command = self.SCPI_cmd_error_seconds
        self.tn.read_until(b"hello", timeout=0.5).decode("ascii").rstrip("\n")

        self.tn.write(command.encode("ascii") + b"\n")
        result_str = self.tn.read_until(b"test", timeout=0.5).decode("ascii").rstrip("\n")

        return result_str

    def test_time(self):
        command = self.SCPI_cmd_time_elapsed

        self.tn.read_until(b"hello", timeout=0.5).decode("ascii").rstrip("\n")

        self.tn.write(command.encode("ascii") + b"\n")
        result_str = self.tn.read_until(b"test", timeout=0.5).decode("ascii").rstrip("\n")

        return result_str











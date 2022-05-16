#Check input power = 0/-5dBm

#Step 1: total disp DCP-M = 0ps/nm
    #initTDCM = Current TDCM value
    #i = 0
    #OK = True


#while OK = true

    #Step 2: Sleep 5 sec, check freq deviation for Link establishment

    #Step 3:
    #If i >= 0
        # If freq deviation=0 -> Step 4
                #Step 4: Toggle laser to get Rx loss (+ wait 2 seconds) -> resets the Pre-FEC BER.
                #Step 5: Read the TRx Pre-FEC_BER by reading 20h:B6-B7
                #Report total disp (i) + Pre-FEC BER to .txt-file
                #i = i + 10

        # Elif frequency deviation > 0
                # Pre-FEC_BER = "-"
                #Report total disp (i) + Pre-FEC BER to .txt-file
                # i = -10

    #If i < 0
        # If freq deviation=0 -> Step 4
                #Step 4: Toggle laser to get Rx loss (+ wait 2 seconds) -> resets the Pre-FEC BER.
                #Step 5: Read the TRx Pre-FEC_BER by reading 20h:B6-B7
                #Report total disp (i) + Pre-FEC BER to .txt-file
                #i = i + 10

        # Elif frequency deviation > 0
                # Pre-FEC_BER = "-"
                #Report total disp (i) + Pre-FEC BER to .txt-file
                # OK = False








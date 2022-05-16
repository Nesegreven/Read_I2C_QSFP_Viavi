###############################################################################
## RC-6000.pl
## Copyright (c) 2011 JDSU
## This script is provided "as-is" and is meant for demonstration purposes only.
##
## Establishes a remote control connection to an MSAM module in a 
## T-BERD/MTS 6000A.
##
## Syntax:
##  perl RC-6000A.pl <unit IP>
## 
## Parameters:
##  <unit IP> - the IP address of the unit
###############################################################################

use strict;
use IO::Socket;
use IO::Select;

# Get script arguments
my $ip = shift @ARGV || usage(); 

# These will always be the module parameters for an MSAM module in an MTS-6000A
my $side = "PWRS";
my $slice = "SLIC1";

# references to the socket and IO::Select objects
my $socket;
my $select;
my $currentPort;

# Install handlers to ensure we disconnect the socket properly if Ctrl+C is pressed
# or if we get an unexpected error
$SIG{__DIE__} = sub { socketClose(); die @_; };
$SIG{INT} = sub { socketClose(); exit; };


# Initial connection
connectToRC($ip, $slice, $side);

# Main loop
while (1) {
    print "\n";
    print "Select:\n";
    print "  1 - Interactive prompt - Standard RC mode with GUI disabled\n";
    print "  2 - Interactive prompt - GUI enabled (for debugging)\n";
    print "  3 - RC demo script using TermOc3Sts1Bert (looks for self-looped SFP in slot 1)\n";
    print "  Q - Quit\n";
    print "> ";
    my $choice = <STDIN>;
    chomp $choice;  # remove newline
    
    if ($choice eq "1") {
        rcPrompt();
    } elsif ($choice eq "2") {
        rcPromptWithGui();
    } elsif ($choice eq "3") {
        rcDemo1();
    } elsif ($choice =~ /^Q/i) {  # if $choice starts with "q" or "Q"
        socketClose();
        exit;
    }
}


# Go through the steps to open a remote control connection
sub connectToRC {
    # get subroutine parameters
    my $ip = shift || die "connectToRC: 'ip' parameter is required";
    my $slice = shift || die "connectToRC: 'slice' parameter is required";
    my $side = shift || die "connectToRC: 'side' parameter is required";
    
    # this is used several times in the first 2 steps... something like BOTH,SLIC1,"BERT"
    my $moduleParams = "$side,$slice,\"BERT\"";
    
    ######################################################################
    # Step 1: Connect to port 8000 and get the module port number
    ######################################################################
    socketOpen($ip, 8000);
    
    socketSend("*REM");
    
    # Verify a BERT module is present in the specified location
    socketSend("MOD:FUNC:LIST? $side,$slice");
    my $resp = socketRead();
    # response should contain the substring "BERT" (quotes included!), otherwise stop
    unless ($resp =~ /"BERT"/) {
        die "BERT module is not present in the specified location, query returned '$resp'";
    }
    
    # Verify the module is on
    socketSend("MOD:FUNC:SEL? $moduleParams");
    $resp = socketRead();
    # response should be ON, otherwise stop
    if ($resp ne "ON") {
        die "The module is not enabled";
    }
    
    # Get the module port number
    socketSend("MOD:FUNC:PORT? $moduleParams");
    my $modulePort = socketRead();
    if ($modulePort eq "-1") {
        die "Unable to obtain the module port number";
    }
    socketClose();
    
    ######################################################################
    # Step 2: Connect to the module port and get the RC port number
    ######################################################################
    socketOpen($ip, $modulePort);
    
    # Allow RC connection to the module
    socketSend("*REM");
    
    # Verify the module is fully booted up and ready for RC connections
    socketSend(":SYST:FUNC:READY? $moduleParams");
    $resp = socketRead();
    # response should be 1, otherwise stop
    if ($resp ne "1") {
        die "The module is not ready";
    }
    
    # Query for the RC port number
    socketSend(":SYST:FUNC:PORT? $moduleParams");
    my $rcPort = socketRead();
    if ($rcPort eq "-1") {
        die "Unable to obtain the RC port number";
    }
    socketClose();

    ######################################################################
    # Step 3: Connect to the RC port
    ######################################################################
    socketOpen($ip, $rcPort);
    
    print "Connection opened to RC port $currentPort\n";
}

# Interactive RC session
sub rcPrompt {
    print "\nStarting RC mode with the GUI disabled...\n";
    # Just sending "*REM" will do the same thing, unless we're already in RC mode with the GUI active.
    # Specify the HIDDEN parameter to ensure the GUI is disabled.
    sendRC("*REM HIDDEN");
    
    # Stop any running applications, restore default settings
    sendRC("*RST");
    
    print "RC mode enabled, no applications are currently running.\n";
    print "Type 'quit' to return to the main menu.\n";
    
    while (1) {
        print "> ";
        my $input = <STDIN>;
        chomp $input;  # remove the newline
        last if (uc $input eq "QUIT");
        
        # Send the command, but don't print it again
        sendRC($input, 1);
    }
}


# Interactive RC session with the application running on the GUI.
# If no applications are running, the script will ask the user to launch one
# If multiple applications are running, the script will use the first one in the :SYST:APPL:CAPP? list
sub rcPromptWithGui {
    print "\nStarting RC mode with the GUI active...\n";
    sendRC("*REM VISIBLE FULL");
    
    # get the list of currently running applications
    my $appList = sendRC(":SYST:APPL:CAPP?");
    
    # make sure we have one running
    while ($appList eq "") {
        print "Please launch an application using the GUI, press ENTER when done...";
        <STDIN>;
        $appList = sendRC(":SYST:APPL:CAPP?");
    }
    
    # if there are more than one, just access the first one in the list
    my @apps = split ",", $appList;
    my $appId = shift @apps;
    
    print "Connecting to $appId...\n";
    sendRC(":SYST:APPL:SEL $appId");
    sendRC(":SESS:CREATE");
    sendRC(":SESS:START");
    # Don't need to send :INIT here, test starts in "Running" state in GUI mode
    
    print "Connected! Enter RC commands or type 'quit' to return to the main menu\n";
    
    while (1) {
        print "> ";
        my $input = <STDIN>;
        chomp $input;   # remove the newline
        last if (uc $input eq "QUIT");
        
        # Send the command, but don't print it again
        sendRC($input, 1);
    }
    sendRC(":SESS:END");
}

# Example script to launch an application, configure and enable the laser,
# and insert and check an alarm
sub rcDemo1 {
    my $appName = "TermOc3Sts1Bert";
    
    print "\nStarting RC mode\n";
    # Usually *REM will work, unless we're in remote control mode already with the GUI enabled.
    # The HIDDEN parameter ensures the GUI will be shut down if it's running.
    sendRC("*REM HIDDEN");
    
    # If we were already in RC mode, there may be other apps still running. *RST will stop these.
    sendRC("*RST");
    
    # launch the application
    print "Launching $appName\n";
    return unless sendRC(":SYST:APPL:LAUN $appName");
    my $appId = sendRC(":SYST:APPL:LAUN?");
    
    # select the application and start the session
    sendRC(":SYST:APPL:SEL $appId");
    sendRC(":SESS:CREATE");
    sendRC(":SESS:START");
    
    # Need to send :INIT here to start the test. Applications begin in the 
    # "Stopped" state in (GUI-disabled) RC mode.
    sendRC(":INIT");
    
    # Assume SFP is in slot 1
    sendRC(":INPut:INTerface:TYPE SFP1");
    
    # Query laser state (should be off), turn it on and verify
    sendRC(":OUTP:OPT?");
    sendRC(":OUTP:OPT ON");
    sleep 1;
    my $state = sendRC(":OUTP:OPT?");
    if ($state ne "ON") {
        print "Tried SFP in slot 1, couldn't enable laser\n";
        return;
    }
    
    # Test restart: equivalent to a test stop and start.
    sendRC(":ABORT");
    sendRC(":INIT");
    
    # Check for signal
    my $signal = sendRC(":SENSe:DATA? CSTatus:PHYSical:SIGNal");
    if ($signal ne "1") {
        print "No signal detected\n";
        return;
    }
    
    # Insert a LOF alarm and check the result
    sendRC(":SOURce:SONet:SECTion:INSert:LOF ON");
    sleep 3;
    my $lofDetected = sendRC(":SENSe:DATA? CSTatus:SONet:SECTion:LOF");
    
    # end session, exit the app
    print "Demo complete! Shutting down application\n";
    sendRC(":SESS:END");
    sendRC(":EXIT");
}


##############################################################################
# Socket connection routines
##############################################################################

# opens a socket and creates an IO::Select object for the given IP and port
# these will be accessible as $socket and $select from anywhere in the script
sub socketOpen {
    my $ip = shift || die "socketSend: 'cmd' parameter is required";
    my $port = shift || die "socketSend: 'port' parameter is required";
    
    print "Opening socket connection to $ip on port $port\n";
    $socket = IO::Socket::INET->new(PeerAddr => $ip,
                                    PeerPort => $port,
                                    Proto => "tcp",
                                    Type => SOCK_STREAM) or die "Can't create socket to port $port";
    # IO::Select allows socket reads to have a timeout
    $select = IO::Select->new($socket);
    $currentPort = $port;
}

# closes the current socket
sub socketClose {
    $select->remove($socket) if (defined $select);
    $select = undef;
    
    $socket->close if (defined $socket);
    $socket = undef;
    print "Socket connection to port $currentPort closed\n\n" if ($currentPort);
    $currentPort = undef;
}

# read a response from the given socket, remove the \n if there is one
sub socketRead {
    # get subroutine parameters
    my $timeout = shift || 90;  # default timeout is 90 seconds
    my $shh = shift;  # if set, don't print the response
    die "Socket must be opened first!" unless (defined $socket and defined $select);
    
    if (not ($select->can_read($timeout))) {
        die "Unable to read from the socket on port $currentPort for $timeout seconds";
    }
    
    my $resp = <$socket>;
    print "$resp" unless ($shh);
    
    # remove the \n
    chomp $resp;
    
    return $resp;
}

# send a message to the given socket, append a \n if there isn't one
sub socketSend {
    # get subroutine parameters
    my $msg = shift || die "socketSend: 'msg' parameter is required";
    my $shh = shift; # if set, don't echo the command we're sending
    
    die "Socket must be opened first!" unless (defined $socket and defined $select);
    
    # add \n if there isn't one at the end of $msg
    $msg .= "\n" unless ($msg =~ /\n$/);
    
    # send it
    print "> $msg" unless ($shh);
    print $socket $msg;
}

# Higher-level routine for communicating with the remote control port
# Query commands: returns the value returned by the command
# Non-query commands: follows up with :SYSTem:ERRor? query, returns 1 if all is well, 0 if there is an error
sub sendRC {
    # get subroutine parameters
    my $cmd = shift || die "sendRC: 'cmd' parameter is required";
    my $shh = shift; # if set, don't echo the command we're sending
    
    die "Socket must be opened first!" unless (defined $socket and defined $select);
    
    socketSend($cmd, $shh);
    my $resp;
    
    # Note: the logic below is here to make the interactive modes of this script 
    # more responsive. Generally, all that is needed is the follow-up :SYST:ERR? 
    # for non-query commands.
    
    # Query commands (if the command has a ?) - return the response
    if ($cmd =~ /\?/) {
        # check if we can read right away
        if ($select->can_read(1)) {
            $resp = socketRead();
            return $resp;
        # if not, there might be a syntax error, check for this
        } else {
            socketSend(":SYST:ERR?");
            if ($select->can_read(1)) {
                my $errResp = socketRead();
                return 0;
            } else {
                # or it might just be taking a while
                $resp = socketRead();
                socketRead(5); # Flush out the response to :SYST:ERR?
                return $resp;
            }
            return $resp;
        }
    }
    # Non-query commands - check for errors
    else {
        socketSend(":SYST:ERR?");
        $resp = socketRead();
        return 1 if ($resp eq '0, "No error"');
        return 0;
    }
}

# Print this message if there was a syntax error
sub usage {
    die <<"EOT";

Syntax:
  perl RC-6000A.pl <unit IP>
 
Parameters:
  <unit IP> - the IP address of the unit

EOT
}
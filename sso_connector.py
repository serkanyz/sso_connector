# -*- coding: utf-8 -*-
'''
***********************************************************************
    Software Name: SSO Connector
    Version Number: 1.16
    Date Written: 01.08.2024
        
    Developer:
        SERKAN YILDIZ     yildiz@serkan.net       www.Serkan.net

    Support and Contact Information : yildiz@serkan.net
    License Information : Open Source
    Platforms Supported by the Software : Python 3.0 or Highder
    Date Information :

    Description:
    SSO Connector facilitates connections to other devices by establishing 
    an SSH/Telnet connection to the Single Connect server.

@author: Serkan YILDIZ yildiz@serkan.net
**********************************************************************
'''

import netmiko
from ttp import ttp
import time
import json
import sys        

# ==============================================================

ttp_template_SSO_Select = """
Search results; 
{{List_ID}}	{{CI_Name}}({{IP_Address}})
"""
net_connect = None
device_type = ""
sso_banner = ""
sso_type = ""
device_banner = ""
sso_log = 1
sso_print = 1

# ==============================================================
#"""Connect to SSO server.
def SSO_Connect(username, password, sso_ip, sso_port, s_type = "terminal_server", rsa_key = None ):
    global net_connect
    global sso_banner
    global sso_type

    try_connection = 2
    
    if rsa_key == None:
        jumpserver = {
            "device_type": s_type,
            "ip": sso_ip,
            "port": sso_port,
            "username": username,
            "password": password,
            "secret": password,
            "timeout": 10,
            "global_delay_factor": 5,
            "banner_timeout": 10}
        if sso_log == 1:
            jumpserver["session_log"] = "SSO_Connector_Session.log.txt"
            
    elif rsa_key != "":
        jumpserver = {
            "device_type": s_type,
            "ip": sso_ip,
            "port": sso_port,
            "username": username,
            "use_keys": True,
            "key_file": r"C:\Users\CSOTECH\.ssh\Nirvana_Linux_RSA",
            "timeout": 10,
            "global_delay_factor": 5,
            "banner_timeout": 10}
        if sso_log == 1:
            jumpserver["session_log"] = "SSO_Connector_Session.log.txt"
        
    while True:
        try:
            net_connect = netmiko.Netmiko(**jumpserver)
            if net_connect.is_alive():
                print("Connected to SSO : " + sso_ip + ":" + str(sso_port))
                sso_banner = Read_Channel()
                print(sso_banner)
                if sso_banner.endswith("$"):
                    sso_type = "linux"
                    netmiko.redispatch(net_connect, device_type="linux")
                elif sso_banner.endswith(":"):
                    sso_type = "terminal_server"
                elif sso_banner.endswith("#"):
                    sso_type = "cisco_ios"
                    netmiko.redispatch(net_connect, device_type="cisco_ios")
                elif sso_banner.endswith(">"):
                    sso_type = "huawei"
                    netmiko.redispatch(net_connect, device_type="huawei")
                else:
                    sso_type = "terminal_server"
                    print("SSO Type didn't find...")
                
                print("SSO Type : " + sso_type)
                
                if "password expired" in sso_banner.lower():
                    SSO_Disconnect()
                    print("SSO Password Expired...")
                    
                return net_connect
        except Exception as e:
            print(e)
            print("SSO Connection failed...")
            print("===============================")

        try_connection -= 1
        if try_connection == 0:
            return "SSO Connection failed..."
        time.sleep(2)

def get_huawei_info():
    output = ''
    try:
        net_connect.write_channel('screen-length 0 temporary\n')
        output = net_connect.send_command("display version", delay_factor=5, read_timeout=30, use_textfsm=False)
    except:
        print("Check device type 1...")
    
    try:
        if len(output) < 200:
            net_connect.write_channel('\r')
            net_connect.write_channel('undo smart\n')
            output = net_connect.send_command("display system sys-info", delay_factor=5, read_timeout=30, use_textfsm=False)
    except:
        print("Check device type 1a...")
    return output

def get_routers_info():
    output = ''
    try:
        net_connect.write_channel('terminal length 0\n')
        #net_connect.write_channel("terminal width 511\n")
        time.sleep(3)
        output = net_connect.send_command("show version", expect_string=r"#", delay_factor=5, read_timeout=30, use_textfsm=False)
        
        if "-sh:" in output or "-bash:" in output:
            output = net_connect.send_command("uname", expect_string=r"#", delay_factor=5, read_timeout=30, use_textfsm=False)
        elif "Command fail." in output:
            output = net_connect.send_command("get system status", expect_string=r"#", delay_factor=5, read_timeout=30, use_textfsm=False)
        elif "Try using help -s" in output:
            output = "globesurfer"
    except:
        print("Check device type 2...")
    return output

def get_routers_info_enable(enable_password):
    output = ''
    try:
        net_connect.write_channel('enable\r')
        time.sleep(3)
        net_connect.write_channel(enable_password + '\r')
        time.sleep(5)
    except Exception as e:
        print(e)
    
    n = 0
    while True:
        try:
            prompt = ""
            prompt = Read_Channel()
        except:
            print("No Prompt...")
            prompt = ""
        #print(prompt)
        if prompt.endswith("#"):
            break
        else:
            n = n+1
            
        if n == 8:
            break
        time.sleep(1)

    try:
        net_connect.write_channel('terminal length 0\r')
        time.sleep(3)
        output = net_connect.send_command("show version", delay_factor=5, read_timeout=60, use_textfsm=False)
    except Exception as e:
        print(e)
        print("Check device type 3...")
        
    #print(output)
    if output.replace(" ", "") == "" :
        output = get_huawei_info()
        #print(output)
    
    return output

def get_linux_info():
    output = ''
    try:
        output = net_connect.send_command("uname -s", delay_factor=5, read_timeout=30, use_textfsm=False)
    except:
        print("Check device type 4...")
    return output

def get_alcatel_info():
    output = ''
    try:
        output = net_connect.send_command("show version", delay_factor=5, read_timeout=30, use_textfsm=False)
    except:
        print("Check device type 4...")
    return output

def Check_Device_Type(enable_password = "NoData"):
    global net_connect
    global device_type
    try:
        if Check_Device_Connection():
            n=0
            while True:
                try:
                    output = Read_Channel()
                    lines = output.splitlines()
                    
                    if lines[-1].startswith('<') and lines[-1].endswith('>'):
                        output = get_huawei_info()
                    elif not lines[-1].startswith('<') and lines[-1].endswith('>') and enable_password != "":
                        output = get_routers_info_enable(enable_password)
                    elif not lines[-1].startswith('<') and lines[-1].endswith('>'):
                        output = get_huawei_info()
                        if len(output) < 200:
                            output = get_routers_info()
                    elif "mediant" in output.lower():
                        device_type = "mediant"
                        return device_type         
                    elif lines[-1][1] == ":" and lines[-1].endswith('#'):
                        output = get_alcatel_info()
                    elif lines[-1].endswith('#'):
                        output = get_routers_info()
                    elif lines[-1].endswith('$'):
                        output = get_linux_info()
                        
                except Exception as e:
                    print(e)

                #print(output)
                # Cihaz türünü belirle
                if "Cisco IOS XR" in output:
                    device_type = "cisco_xr"
                elif "Cisco Nexus Operating System" in output:
                    device_type = "cisco_nxos"
                elif "Cisco IOS XE" in output:
                    device_type = "cisco_xe"
                elif "Cisco IOS Software" in output:
                    device_type = "cisco_ios"
                elif "Cisco AP Software" in output:
                    device_type = "cisco_ap"
                elif "Active-image:" in output and "flash:" in output:
                    device_type = "cisco_cbs"
                elif "Image stamp:" in output:
                    device_type = "hp_procurve"
                elif "The main service identification of this node" in output or "Mainboard Running Area Information" in output:
                    device_type = "huawei_olt" 
                elif "Huawei Versatile Routing Platform Software" in output or "Huawei Technologies Co." in output:
                    device_type = "huawei"
                elif "Nokia" in output and "IXR" in output:
                    device_type = "nokia_sros"
                elif "junos" in output.lower():
                    device_type = "juniper_junos"
                elif "linux" in output.lower():
                    device_type = "linux"
                elif "mediant" in output.lower():
                    device_type = "mediant"
                elif "zte corporation" in output.lower() or " zte " in output.lower() :
                    device_type = "zte_zxros"
                elif ("alcatel" in output.lower() or "nokia" in output.lower()) and "timos" in output.lower():
                    device_type = "alcatel_sros"
                elif "ricon" in output.lower() or ("Device Model" in output and "Hardware Version" in output and "Software Version" in output and "Serial Number" in output):
                    device_type = "ricon"
                elif "fortigate" in output.lower() or "fortinet" in output.lower():
                    device_type = "fortinet"
                elif "globesurfer" in output.lower():
                    device_type = "globesurfer"
                elif "arubaos" in output.lower():
                    device_type = "aruba_os"
                
                
                if "cisco" in device_type:
                    net_connect.write_channel('terminal length 0\r')
                    net_connect.write_channel('terminal width 512\r')
                    n = 0
                    while True:
                        if "#" in Read_Channel():
                            break
                        elif n == 10:
                            break
                        n += 1
                elif device_type == "huawei":
                    net_connect.write_channel('screen-length 0 temporary\r')
                elif device_type == "huawei_olt":
                    net_connect.write_channel('undo smart\r')
                    net_connect.write_channel('scroll 512\r')
                    
                if device_type != "":
                    print(f"Device Type: {device_type}")
                    return device_type
                
                time.sleep(1)
                n = n+1
                if n == 8:
                    device_type = "unknown"
                    return device_type
        else:
            device_type = "unknown"
            return device_type
    except:
        print("Device type could not be determined...")
        device_type = "unknown"
        return device_type

def Pass_Try(host, susername, spassword, Remote_host_conn):
    prompt = Remote_host_conn
    #print(Remote_host_conn)
    try:
        n=0
        while True:
            n+=1

            if prompt=="":
                pass
            elif "username:" in prompt.lower() or "login:" in prompt.lower() or "user name" in prompt.lower() or "user:" in prompt.lower():
                time.sleep(1)
                print(susername)
                net_connect.write_channel(susername+'\n')
                time.sleep(2)
                print(spassword)
                net_connect.write_channel(spassword+'\n')
      
            elif "password:" in prompt.lower():
                print(spassword)
                net_connect.write_channel(spassword+'\r')
                print("Password tried...")

            elif prompt[-1]==">" or prompt[-1]=="#" or prompt[-1]=="]":
                return 1
            
            elif "No such user:" in prompt:
                net_connect.write_channel('\n')
                net_connect.write_channel('\n')
                net_connect.write_channel('\n')
                return 0
            
            elif prompt[-1]=="$":
                return 0
            
            elif "Change now?" in prompt or "[y/n]" in prompt.lower():
                net_connect.write_channel('N\n')
                time.sleep(1)
                net_connect.write_channel('\n')
                print("Attention : Password change required...")
                return 0

            elif "old password:" in prompt.lower():
                net_connect.write_channel('\n')
                net_connect.write_channel('\n')
                net_connect.write_channel('\n')
                print("Attention : Password change required...")
                return 0
            
            elif "Please retry after" in prompt:
                time.sleep(5)
                
            else:
                print("Trying again...")
            
            try:
                time.sleep(0.5)
                prompt=""
                prompt = net_connect.find_prompt(delay_factor=10)
                print(prompt)
            except Exception as e:
                print(e)
                
            if n == 4:
                return 0
            
    except Exception as e:
        print(e)
        return 0
    
# SSO bağlantısı üzerinden bir cihaza bağlantı sağlar.
def Device_Connect(host, port = 22, mode = "ssh", susername = None, spassword = None, enable_password = None, remote_device_type="terminal_server"):
    global net_connect
    global device_type
    global device_banner
    
    try:
        netmiko.redispatch(net_connect, device_type="terminal_server")
        net_connect.write_channel("\r")
        output = net_connect.read_channel()
        n=0
        while True:
            n+=1
            if output.replace(" ", "") == "":
                net_connect.write_channel("\r")
                output = net_connect.read_channel()
                print("%% No Response %%")
            else:
                break
            if n == 5:
                break
            time.sleep(0.5)

        if "Type to search or select one" in output:
            net_connect.write_channel(str(host) + "\r\n")
            time.sleep(1)
            device_banner = net_connect.read_channel()
            print("Connecting to Device = " + host, end=" ")

            n=0
            while True:
                time.sleep(0.5)
                try:
                    net_connect.write_channel(" \r")
                    output = net_connect.read_channel()
                    if device_banner == "":
                        device_banner = output
                except Exception as e:
                    print(e)
                    if "Socket is closed" in e:
                        return "unsuccessful"
                    continue
                
                if len(output) == 0:
                    print(".", end=" ")
                elif "Type '*' to clear search" in output:
                    net_connect.write_channel("*\r\n")
                    net_connect.write_channel("\r")
                    return "unsuccessful"
                
                elif "Connected" in output:
                    time.sleep(1)
                    net_connect.write_channel("\r")
                elif ("#" in output or ">" in output) and ("Type to search or select one" not in output):
                    print("Connected to device...")
                    
                    if remote_device_type == 'terminal_server':
                        device_type = Check_Device_Type()
                        
                        if device_type != "unknown" and device_type !="":
                            try:
                                if device_type == "zte_zxros":
                                    current_prompt = net_connect.find_prompt()
                                    net_connect.base_prompt = current_prompt.strip("#").strip()
                                
                                netmiko.redispatch(net_connect, device_type=device_type)
                                
                            except Exception as e:
                                print(e)
                    else:
                        try:
                            device_type = remote_device_type
                            
                            netmiko.redispatch(net_connect, device_type=device_type)
                            print(f"Device Type: {device_type}")
                            
                        except Exception as e:
                            print(e)
                            
                    return device_type

                elif "Do you want to proceed with Management IP Detection" in output:
                    net_connect.write_channel(" n\r\n")
                    time.sleep(1)
                    #net_connect.write_channel("*\r\n")
                    print("Device not found...")
                    return "unsuccessful"
                
                elif "Search results;" in output:
                    parser = ttp(data=output, template=ttp_template_SSO_Select)
                    parser.parse()
                    results = parser.result(format="json")[0]
                    result_list = json.loads(results)  # string to liste
                    # print(result_list)
                    loopid = 0
                    for i in result_list[0]:
                        # print(i)
                        if i["IP_Address"] == host:
                            loopid = 1
                            net_connect.write_channel(i["List_ID"] + "\r\n")
                            break
                    if loopid == 0:
                        print("Device not found from search results...")
                        net_connect.write_channel("*\r\n")
                        net_connect.write_channel("\r")
                        return "unsuccessful"
                elif "Connecting to device" in output:
                    time.sleep(3)
                elif "Press any key" in output:
                    net_connect.write_channel("\r")
                    net_connect.write_channel("\r")
                    print("Connection could not be established...")
                    return "unsuccessful"
                elif "Type to search or select one" in output:
                    print("Connection could not be established...")
                    return "unsuccessful"
                else:
                    print(".", end=" ")
                    
                if n == 100:
                    print(n)
                    print("Connection could not be established...")
                    SSO_Disconnect()
                    return "unsuccessful"
                n=n+1
                
        elif "$" in output:
            print("Connecting to Device = " + host, end=" ")
            
            if susername == None:
                print("Attention : Username is empty. Please give username for device...")
            
            try:
                if mode == "telnet":
                    Remote_host_conn = net_connect._send_command_str(
                    "telnet"+" "+ str(host)+ "\r\n",
                    expect_string=r":",
                    strip_prompt=False,
                    strip_command=False,
                    read_timeout=240,
                    delay_factor=15
                    )
                elif mode == "ssh":
                    
                    #Attention: This command removes the SSH host key for the specified host from your local ~/.ssh/known_hosts file.
                    net_connect.write_channel("ssh-keygen -R "+ host + "\r")  
                    
                    time.sleep(0.5)
                    Remote_host_conn = net_connect._send_command_str(
                    "ssh -l "+ susername +" "+ str(host)+ " \r\n",
                    expect_string=r":",
                    strip_prompt=False,
                    strip_command=False,
                    read_timeout=240
                    )
                    
                    if "diffie-hellman" in Remote_host_conn or "DH GEX group" in Remote_host_conn:
                        net_connect.write_channel("\n\r")
                        time.sleep(0.5)
                        Remote_host_conn = net_connect._send_command_str(
                        "ssh -oKexAlgorithms=+diffie-hellman-group1-sha1 -oHostKeyAlgorithms=+ssh-rsa -l "+ susername +" "+ str(host)+ " \r\n",
                        expect_string=r":",
                        strip_prompt=False,
                        strip_command=False,
                        read_timeout=240
                        )
                        
                elif mode == "ssh-diffie-hellman":
                    net_connect.write_channel("ssh-keygen -R "+ host + "\r")
                    time.sleep(0.5)
                    Remote_host_conn = net_connect._send_command_str(
                    "ssh -oKexAlgorithms=+diffie-hellman-group1-sha1 -oHostKeyAlgorithms=+ssh-rsa -l "+ susername +" "+ str(host)+ " \r\n",
                    expect_string=r":",
                    strip_prompt=False,
                    strip_command=False,
                    read_timeout=240
                    )

            except Exception as e:
                print(e)
                return "unsuccessful"
            
            device_banner = Remote_host_conn
            #print(Remote_host_conn)
            for i in range(4):
                if "kex_exchange_identification" in Remote_host_conn:
                    print("Mesaj : kex_exchange_identification: read: Connection reset by peer")
                    return "unsuccessful"
                elif "Host key verification failed" in Remote_host_conn:
                    print("Mesaj : Host key verification failed...")
                    return "unsuccessful"
                elif "fingerprint" in Remote_host_conn:
                    print("SSH Key Verification...")
                    try:
                        time.sleep(1)
                        net_connect.write_channel('yes\n')
                        print("SSH Key verified...")
                        time.sleep(2)
                        Remote_host_conn = net_connect.read_channel()
                        device_banner += Remote_host_conn
                        print(device_banner)
                        
                        try:
                            if spassword == None:
                                print("Attention : Password is empty. Please give password for device...")
                            PassTry = Pass_Try(host, susername, spassword, Remote_host_conn)
                            if PassTry == 0:
                                Device_Disconnect()
                                return "unsuccessful"
                        except Exception as e:
                            print(e)
                            return "unsuccessful"
                        
                        try:
                            if Check_Device_Connection():
                                device_type = Check_Device_Type(enable_password)
                                return device_type
                        except Exception as e:
                            print(e)
                            print("Message : Could not connect to the device...")
                            return "unsuccessful"
                        
                    except Exception as e:
                        print(e)
                        
                elif "diffie-hellman" in Remote_host_conn:
                    print("Message : Please select ssh-diffie-hellman mode...")
                    return "unsuccessful"
                
                elif "username:" in Remote_host_conn.lower() or "password:" in Remote_host_conn.lower() or "login:" in Remote_host_conn.lower() or "user name" in Remote_host_conn.lower() or "user:" in Remote_host_conn.lower():
                    try:
                        if spassword == None:
                            print("Attention : Password is empty. Please give password for device...")
                        PassTry = Pass_Try(host, susername, spassword, Remote_host_conn)
                        if PassTry == 0:
                            Device_Disconnect()
                            return "unsuccessful"
                    except Exception as e:
                        print(e)
                        return "unsuccessful"

                    try:
                        if Check_Device_Connection():
                            device_type = Check_Device_Type(enable_password)
                            return device_type
                    except Exception as e:
                        print(e)
                        print("Message : Could not connect to the device...")
                        return "unsuccessful"
                    
                elif "$" in Remote_host_conn:
                    print("Message : Could not connect to the device...")
                    return "unsuccessful"
                
                time.sleep(0.5)
                net_connect.write_channel("\r")
                Remote_host_conn = net_connect.read_channel()
                
        else:
            print("No SSO Prompt...")
            SSO_Disconnect()
            return "unsuccessful"
    except Exception as e:
        print("Device connection cannot be established...")
        
    return "unsuccessful"

#=================Check Connections====================================

#***Check SSO Connection
def Check_SSO_Connection():
    global net_connect
    if sso_print == 1:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    try:
        if net_connect.is_alive():
            if sso_print == 1:
                print("Connected to SSO - " + current_time)
            return True
        else:
            if sso_print == 1:
                print("Disconnected to SSO - " + current_time)
            return False
    except Exception as e:
        print("SSO connection cannot be established...")
        return False

#***Check Device Connection
def Check_Device_Connection():
    global net_connect
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    output = "...."
    n = 0
    while True:
        time.sleep(0.5)
        try:
            net_connect.write_channel("\r")
            output = net_connect.read_channel()
        except:
            print("Check: Connection fail...")
            if Check_SSO_Connection():
                pass
            else:
                print("Check: Disconnected to SSO and Device")
                return False
        n = n + 1
        if n == 30:
            try:
                net_connect.send_command_timing('\x036 \r')
            except Exception as e:
                print(e)
            if sso_print == 1:
                print("CTRL+Z")
                print("Check: Disconnected to Device:n")
            return False
        elif "Type to search or select one" in output:
            if sso_print == 1:
                print("Check: Disconnected to Device")
            return False
        elif "$" in output:
            if sso_print == 1:
                print("Disconnected to Device")
            return False
        elif len(output) == 0:
            continue
        elif ("#" in output or ">" in output) and ("Type to search or select one" not in output):
            if sso_print == 1:
                print("Check: Connected to Device")
            return True
        elif "Type to search or select one" in output:
            if sso_print == 1:
                print("Check: Disconnected to Device")
            return False

#=================Disconnect====================================

#"""SSO Connection...
def SSO_Disconnect():
    global net_connect
    global sso_type
    try:
        if net_connect.is_alive():
            try:
                netmiko.redispatch(net_connect, device_type=sso_type)
                net_connect.disconnect()
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                
                if net_connect.is_alive():
                    if sso_print == 1:
                        print("Connected to SSO - " + current_time)
                    return "connected"
                else:
                    if sso_print == 1:
                        print("Disconnected to SSO - " + current_time)
                    return "disconnected"
                
            except:
                print("SSO connection is not available...")
        else:
            print("There's no connection anyway.")
    except:
        return "disconnected"
    
#***Remote Device Connection...
def Device_Disconnect():
    global net_connect
    
    output = "...."
    n = 0
    if Check_Device_Connection():
        while True:
            time.sleep(0.5)
            try:
                net_connect.write_channel("\r\n")
                output = net_connect.read_channel()
            except:
                print("No Data...")
                break
            
            try:
                n = n + 1
                if n == 30:
                    net_connect.send_command_timing('\x1A')
                    if sso_print == 1:
                        print("CTRL+Z")
                        print("Disconnect: Disconnected to Device...n")
                    return "disconnected"
                elif len(output) == 0:
                    print(".", end=" ")
                    if n == 30:
                        SSO_Disconnect()
                        return "disconnected"
                    continue
                elif "Type to search or select one" in output:
                    if sso_print == 1:
                        print("Disconnect: Disconnected to Device...*")
                    return "disconnected"
                elif "$" in output:
                    if sso_print == 1:
                        print("Disconnected to Device...*")
                    return "disconnected"
                elif "Press any key to continue" in output:
                    net_connect.write_channel("\r")
                    if sso_print == 1:
                        print("Disconnect: Disconnected to Device...")
                    return "disconnected"
                elif "Type '*' to clear search" in output:
                    if sso_print == 1:
                        print("Type '*' to clear search")
                    net_connect.write_channel("\r\n")
                    net_connect.write_channel("\r")
                    return "disconnected"
    
                if "cisco" in device_type:
                    net_connect.write_channel("exit\r")
                elif "nokia" in device_type or "alcatel" in device_type:
                    net_connect.write_channel("logout\r")
                elif "huawei_olt" in device_type:
                    net_connect.write_channel("quit\r")
                    net_connect.write_channel("y\r")
                elif "huawei" in device_type:
                    if "[" in output and "]" in output:
                        net_connect.write_channel("return\r")
                    net_connect.write_channel("quit\r")
                else:
                    for cmd in ["exit", "quit", "logout", "y"]:
                        net_connect.write_channel(cmd + "\r")
                        
            except Exception as e:
                print(e)
    else:
        return "disconnected"

#=================Get Info====================================

#***Read prompt
def Read_Channel():
    global net_connect
    n = 0
    output = ''
    #print("Read channel:", end=" ")
    while True:
        time.sleep(0.5)
        try:
            net_connect.write_channel("\r")
            output = net_connect.read_channel()
        except:
            print("Prompt unreadable...")
        if len(output) > 0:
            output = output.strip()
            return output
        if n == 10:
            return "No_Response"
        else:
            n = n + 1

def Read_Just():
    global net_connect
    output = ''
    try:
        output = net_connect.read_channel()
        
        if len(output) > 0:
            return output
        else:
            output = net_connect.find_prompt()
        
    except:
        print("Prompt unreadable...")
    return output

#=================Run Commands====================================

# Send Command
def Run_Command(command, textfsm=False, read_timeout=10):
    global net_connect
    if sso_print == 1:
        print(command)

    try:
        command_answer = ""
        try:
            command_answer = net_connect.send_command(command, use_textfsm=textfsm, read_timeout=read_timeout)
        except:
            try:
                net_connect.write_channel("\r")
                prompt = net_connect.find_prompt()
                print(prompt)
                if any(x in prompt.lower() for x in ["continue?", "y/n", "logout."]):
                    net_connect.write_channel("Y\r")
                    command_answer = net_connect.read_channel()
                    time.sleep(1)
                    command_answer += net_connect.read_channel()
                else:
                    command_answer = prompt
            except Exception as e:
                print(e)
        
        if "Authorization expired" in command_answer:
            print("Authorization expired")
        return command_answer
        
    except Exception as e:
        print("Command could not be sent...")
        print(e)
        return None

# No response is expected for the commands sent with this function.
def Run_Command_NoResponse(command):
    global net_connect
    if sso_print == 1:
        print(command)
    try:
        net_connect.write_channel(command + '\n')
    except Exception as e:
        print("Command could not be sent...")
        print(e)

# Send Command Timing
def Run_Command_Timing(command, read_timeout = 5):
    global net_connect
    if sso_print == 1:
        print(command)
    try:
        command_answer = ""
        try:

            command_answer = net_connect.send_command_timing(command, read_timeout = read_timeout)

            if '--More--' in command_answer:
                command_answer += net_connect.send_command_timing(" ", strip_prompt=False, strip_command=False)
        except:
            try:
                net_connect.write_channel("\r")
                prompt = net_connect.find_prompt()
                print(prompt)
                if any(x in prompt.lower() for x in ["continue?", "y/n", "logout."]):
                    net_connect.write_channel("Y\n")
                    command_answer = net_connect.read_channel()
                    time.sleep(1)
                    command_answer += net_connect.read_channel()
            except Exception as e:
                print(e)

        return command_answer
    except Exception as e:
        print("Command could not be sent...")
        print(e)
        return None

#=================End Modul====================================





















'''
***********************************************************************

    Software Name: SSO Connector

    @author: Serkan YILDIZ yildiz@serkan.net
    
**********************************************************************
'''


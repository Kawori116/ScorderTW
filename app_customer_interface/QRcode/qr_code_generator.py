from cryptography.fernet import Fernet
import os
import qrcode

# Generate and save a key
# def generate_key():
#     key = Fernet.generate_key()

#     with open("secret.key", "wb") as key_file:
#         key_file.write(key)

def load_key():
    secret_key = '0iseESfRYHk-4PQuAhXDCp64iUnN-bFIPZlYLDUHJNg='
    return secret_key

def encrypt_data(data):
    key = load_key()
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())

    return encrypted_data.decode()

def generate_qr_code():
    
    for table_number in range(1, 5):
        data_to_encrypt = f"{table_number}"
        encrypted_table_number = encrypt_data(data_to_encrypt)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        print('http://localhost:8000/app_customer/{encrypted_table_number}/handle_qr/')
        qr.add_data(f'http://localhost:8000/app_customer/{encrypted_table_number}/handle_qr/')
        # qr.add_data(f'http://172.20.10.3:8000/app_customer/{encrypted_table_number}/handle_in_qr/')
        # qr.add_data(f'https://846541643132163845.com/app_customer/{encrypted_table_number}/')
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        dir_path = "qrcode-images"
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        file_path = os.path.join(dir_path, f"qr-dine-in-{table_number}.png")
        print(f"Generated dine-in QR for table {table_number}: {file_path}")

        qr_img.save(file_path)

    # Generate single QR code for takeout/delivery selection
    generate_takeout_delivery_qr()

def generate_takeout_delivery_qr():
    """Generate single QR code for takeout and delivery selection"""
    data_to_encrypt = "out"
    takeout_delivery = encrypt_data(data_to_encrypt)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Single URL that leads to order type selection page
    qr.add_data(f'http://localhost:8000/app_customer/{takeout_delivery}/handle_qr/')
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    dir_path = "qrcode-images"
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    
    file_path = os.path.join(dir_path, "qr-takeout-delivery.png")
    qr_img.save(file_path)
    print(f"Generated QR code for takeout/delivery selection: {file_path}")
# cd \app_customer_interface
# cd QRcode
# > python -v qr_code_generator.py
        
if __name__ == "__main__":
    # generate_key() # Uncomment to generate a new key
    generate_qr_code()

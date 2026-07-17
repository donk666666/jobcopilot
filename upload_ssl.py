import paramiko
import os
import base64

# Use Windows temp dir (where git bash /tmp maps to)
temp_dir = os.environ.get('TEMP', '') or os.environ.get('TMP', '')
ssl_dir = os.path.join(temp_dir, 'ssl_upload', 'smartdocqa.top_nginx')

cert_path = os.path.join(ssl_dir, 'smartdocqa.top_bundle.crt')
key_path = os.path.join(ssl_dir, 'smartdocqa.top.key')

print(f'Reading cert from: {cert_path}')
print(f'Reading key from: {key_path}')

with open(cert_path, 'rb') as f:
    cert_data = f.read()
with open(key_path, 'rb') as f:
    key_data = f.read()

cert_b64 = base64.b64encode(cert_data).decode()
key_b64 = base64.b64encode(key_data).decode()

print(f'Cert: {len(cert_data)} bytes, Key: {len(key_data)} bytes')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('119.91.213.156', username='ubuntu', password='@%j6HXT^K}3Qv')

ssh.exec_command('sudo mkdir -p /etc/nginx/ssl')

# Write base64 to server then decode
# Write cert_b64 to a temp file on server first, then decode
stdin, stdout, stderr = ssh.exec_command('sudo tee /tmp/cert.b64')
stdin.write(cert_b64)
stdin.channel.shutdown_write()
stdout.channel.recv_exit_status()
print('Cert b64 uploaded')

stdin, stdout, stderr = ssh.exec_command('sudo tee /tmp/key.b64')
stdin.write(key_b64)
stdin.channel.shutdown_write()
stdout.channel.recv_exit_status()
print('Key b64 uploaded')

# Decode
stdin, stdout, stderr = ssh.exec_command('sudo base64 -d /tmp/cert.b64 | sudo tee /etc/nginx/ssl/smartdocqa.top_bundle.crt > /dev/null && echo "cert ok"')
stdout.channel.recv_exit_status()
print(stdout.read().decode().strip())

stdin, stdout, stderr = ssh.exec_command('sudo base64 -d /tmp/key.b64 | sudo tee /etc/nginx/ssl/smartdocqa.top.key > /dev/null && echo "key ok"')
stdout.channel.recv_exit_status()
print(stdout.read().decode().strip())

ssh.exec_command('sudo chmod 600 /etc/nginx/ssl/smartdocqa.top.key')
ssh.exec_command('sudo chmod 644 /etc/nginx/ssl/smartdocqa.top_bundle.crt')

# Verify
stdin, stdout, stderr = ssh.exec_command('ls -la /etc/nginx/ssl/')
stdout.channel.recv_exit_status()
print(stdout.read().decode())

# Cleanup temp files
ssh.exec_command('sudo rm -f /tmp/cert.b64 /tmp/key.b64')

# Nginx HTTPS config
config = '''server {
    listen 443 ssl http2;
    server_name smartdocqa.top www.smartdocqa.top;

    ssl_certificate /etc/nginx/ssl/smartdocqa.top_bundle.crt;
    ssl_certificate_key /etc/nginx/ssl/smartdocqa.top.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}

server {
    listen 80;
    server_name smartdocqa.top www.smartdocqa.top;
    return 301 https://$host$request_uri;
}
'''

stdin, stdout, stderr = ssh.exec_command('sudo tee /etc/nginx/sites-available/smartdocqa')
stdin.write(config)
stdin.channel.shutdown_write()
stdout.channel.recv_exit_status()

ssh.exec_command('sudo ln -sf /etc/nginx/sites-available/smartdocqa /etc/nginx/sites-enabled/')
ssh.exec_command('sudo rm -f /etc/nginx/sites-enabled/default')

stdin, stdout, stderr = ssh.exec_command('sudo nginx -t && sudo systemctl reload nginx')
stdout.channel.recv_exit_status()
print('Nginx:', stdout.read().decode().strip())
print('Err:', stderr.read().decode().strip())

ssh.close()
print('Done!')

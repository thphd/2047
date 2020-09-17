from commons import *
import os

init_directory('./temp')

def verify(pk, msg):
    # obtain a temp filename
    fn = get_random_hex_string(10)

    # save the public key file and the message file
    with open(f'./temp/{fn}.pk', 'w', encoding='ascii') as f:
        f.write(pk)

    with open(f'./temp/{fn}.msg', 'w', encoding='ascii') as f:
        f.write(msg)

    # remove armor
    status = os.system(f'gpg --dearmor ./temp/{fn}.pk')
    if status != 0:
        print('status:', status)
        raise Exception('failed to dearmor the public key')

    # verify
    status = os.system(f'gpg --no-default-keyring --keyring ./temp/{fn}.pk.gpg --verify ./temp/{fn}.msg')
    if status != 0:
        print('status:', status)
        raise Exception('failed to verify the message')

    return True

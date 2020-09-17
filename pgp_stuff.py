from commons import *
import os

init_directory('./temp')

# gpg must exist on your system
status = os.system('gpg --version')
if status==0:
    print_up('gpg is found')
else:
    print_err('can\'t find gpg')

def verify_publickey_message(pk, msg):
    # obtain a temp filename
    fn = get_random_hex_string(10)

    # save the public key file and the message file
    pkfn = f'./temp/{fn}.pk'
    pkbinfn = pkfn+'.gpg'
    msgfn = f'./temp/{fn}.msg'

    with open(pkfn, 'w', encoding='ascii') as f:
        f.write(pk)

    with open(msgfn, 'w', encoding='ascii') as f:
        f.write(msg)

    # remove armor
    status = os.system(f'gpg --dearmor {pkfn}')
    if status != 0:
        print('status:', status)

        os.remove(pkfn)
        os.remove(msgfn)

        raise Exception('failed to dearmor the public key')

    os.remove(pkfn)

    # verify
    status = os.system(f'gpg --no-default-keyring --keyring {pkbinfn} --verify {msgfn}')
    if status != 0:
        print('status:', status)

        os.remove(pkbinfn)
        os.remove(msgfn)

        raise Exception('failed to verify the message')

    os.remove(pkbinfn)
    os.remove(msgfn)

    return True

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

    writefile(pkfn, pk, mode='w', encoding='utf-8')
    writefile(msgfn, msg, mode='w', encoding='utf-8')

    def cleanup():
        removefile(pkfn)
        removefile(msgfn)
        removefile(pkbinfn)

    # remove armor
    status = os.system(f'gpg --dearmor {pkfn}')
    if status != 0:
        print('status:', status)
        cleanup()
        raise Exception('failed to dearmor the public key (there might be something wrong with your public key)')

    # verify
    status = os.system(f'gpg --no-default-keyring --keyring {pkbinfn} --verify {msgfn}')
    if status != 0:
        print('status:', status)
        cleanup()
        raise Exception('failed to verify the message (your public key is okay but the signature you supplied does not match the public key, or is of a wrong format)')

    cleanup()
    return True

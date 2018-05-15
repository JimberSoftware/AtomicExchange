# Initiator class will initiate contact with acceptor to start the atomic swap

from __future__ import print_function

import grpc

import atomicswap_pb2
import atomicswap_pb2_grpc
from optparse import OptionParser

import os
import json
from collections import namedtuple

from dry_run import InitiatorDryRun

def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())
def json2obj(data): return json.loads(data, object_hook=_json_object_hook)


def execute(process):
    
    global dry_run

    if dry_run:
        dry = InitiatorDryRun()
        return dry.processCommand(process)
    

    process = os.popen(process)
    output = reprocessed = process.read()
    process.close()
    
    return output.rstrip()

def run(initiator_amount, acceptor_amount):
    channel = grpc.insecure_channel('localhost:50051')
    stub = atomicswap_pb2_grpc.AtomicSwapStub(channel)


    response = stub.ProcessInitiate(atomicswap_pb2.Initiate(initiator_amount=initiator_amount, acceptor_amount=acceptor_amount))
    #response.python -m pip install grpcio
    print("Initiator: ")
    print(response.acceptor_address)
    btc_atomicswap_json = execute("btcatomicswap --testnet --rpcuser=user --rpcpass=pass initiate {} {}".format(response.acceptor_address, initiator_amount))
    #do atomic swap


    btc_atomicswap = json2obj(btc_atomicswap_json)
    
    
    initiator_wallet_address =  execute("rivinec wallet address")
    

    response = stub.ProcessInitiateSwap(atomicswap_pb2.InitiateSwap(hash=btc_atomicswap.hash, contract=btc_atomicswap.contract, transaction=btc_atomicswap.contractTransaction, initiator_wallet_address=initiator_wallet_address))

    acceptor_swap_address = response.acceptor_swap_address
    print("Initiator acceptor_swap_address {}".format(acceptor_swap_address))


    audit_swap_json = execute("rivinec atomicswap --testnet audit".format(acceptor_swap_address))
    audit_swap = json2obj(audit_swap_json)


    print("{} = {}".format(float(audit_swap.contractValue), acceptor_amount))
    print(float(audit_swap.contractValue) == acceptor_amount)
    print("{} > {}".format(audit_swap.lockTime, 20))
    print(int(audit_swap.lockTime) > 20)
    print("{} = {}".format(audit_swap.hash, btc_atomicswap.hash))
    print(audit_swap.hash == btc_atomicswap.hash)
    print("{} = {}".format(audit_swap.recipientAddress, initiator_wallet_address))
    print(audit_swap.recipientAddress == initiator_wallet_address)

    if(float(audit_swap.contractValue) != acceptor_amount or int(audit_swap.lockTime) < 20 or audit_swap.hash != btc_atomicswap.hash or audit_swap.recipientAddress != initiator_wallet_address):
        print("Initiator: contract invalid")
        exit(1) #redeem my money after 24h


    redeem_cmd = "rivinec atomicswap redeem {} {} {} {} {} {} {}".format(acceptor_swap_address, acceptor_amount, audit_swap.refundAddress, initiator_wallet_address, btc_atomicswap.hash, audit_swap.lockTime, btc_atomicswap.secret)
    
  
    redeem =  execute(redeem_cmd)
    #check if redeem success here
    response = stub.ProcessRedeemed(atomicswap_pb2.RedeemFinished(finished=True))

dry_run = False

if __name__ == '__main__':
    
    parser = OptionParser()

    parser.add_option("-m", "--my-amount", dest="initiator_amount",
                    help="Your amount of your currency to swap", metavar="INITIATORAMOUNT")

    parser.add_option("-o", "--other-amount",
                    dest="acceptor_amount", default=True,
                    help="The amount of the other partners currency to swap")
    
    parser.add_option("-d", "--dry-run", action="store_true",
                        dest="dry_run",  help="Do a dry run with dummy data")

   
    
    (options, args) = parser.parse_args()
    dry_run = options.dry_run
  
    run(float(options.initiator_amount), float(options.acceptor_amount))

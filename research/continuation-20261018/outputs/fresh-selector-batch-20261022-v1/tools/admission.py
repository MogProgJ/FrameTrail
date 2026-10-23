"""Require authenticated default account and eligible association; scheduler admission is additional."""
import argparse,getpass
from pathlib import Path
def account(folder,user):
    folder=Path(folder)
    defaults=[r.split('|') for r in (folder/'user-default.txt').read_text().splitlines() if r.strip()]
    accounts={r[1] for r in defaults if len(r)>=2 and r[0]==user and r[1]}
    if len(accounts)!=1:raise ValueError('Cannot determine one authenticated default account')
    selected=accounts.pop();assoc=[r.split('|') for r in (folder/'account-limits.txt').read_text().splitlines() if r.strip()]
    if not any(len(r)>=7 and r[0]==user and r[1]==selected and r[2] in ('','gpu_a100_il') for r in assoc):raise ValueError('No matching live account association')
    if not (folder/'qos-live.txt').read_text().strip() or 'PartitionName=gpu_a100_il' not in (folder/'partition-live.txt').read_text():raise ValueError('Missing live QOS/partition evidence')
    return selected
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('folder',type=Path);v=a.parse_args();print(account(v.folder,getpass.getuser()))

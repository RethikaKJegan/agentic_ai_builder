"""Run Phase 6 checks in a private disposable PostgreSQL cluster, then stop it."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--postgres-bin',type=Path,help='Directory containing initdb and pg_ctl.')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    binary=args.postgres_bin
    if binary is None:
        found=shutil.which('initdb')
        candidates=sorted(Path('/usr/lib/postgresql').glob('*/bin/initdb'))
        binary=Path(found).parent if found else candidates[-1].parent if candidates else None
    if binary is None or not all((binary/name).is_file() for name in ('initdb','pg_ctl')):
        parser.error('Install PostgreSQL binaries or supply --postgres-bin; no database was changed.')
    base=Path(tempfile.mkdtemp(prefix='phase6-postgres-'))
    socket=base/'socket';socket.mkdir(mode=0o700);data=base/'data'
    try:
        subprocess.run([str(binary/'initdb'),'-D',str(data),'-A','trust','--no-locale','--encoding=UTF8'],check=True,stdout=subprocess.DEVNULL)
        # Unix socket in a private mode-0700 directory; no TCP listener.
        subprocess.run([str(binary/'pg_ctl'),'-D',str(data),'-l',str(base/'server.log'),'-o',f"-F -h '' -k {socket} -p 55439",'-w','start'],check=True,stdout=subprocess.DEVNULL)
        env=dict(os.environ,BUILDER_TEST_POSTGRES_DSN=f'postgresql:///postgres?host={socket}&port=55439')
        result=subprocess.run([sys.executable,'-m','pytest','tests/test_generic_lifecycle_postgres.py','-q','-rs'],cwd=root,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        print(result.stdout)
        (base/'test-result.txt').write_text(result.stdout)
        print('Disposable PostgreSQL artifacts:',base)
        return result.returncode
    finally:
        if (data/'postmaster.pid').exists():
            subprocess.run([str(binary/'pg_ctl'),'-D',str(data),'-m','fast','-w','stop'],check=True,stdout=subprocess.DEVNULL)


if __name__=='__main__':sys.exit(main())

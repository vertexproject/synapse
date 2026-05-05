import sys
import socket
import asyncio
import logging
import subprocess

import synapse.telepath as s_telepath

import synapse.lib.base as s_base

logger = logging.getLogger(__name__)

class ReaderManager(s_base.Base):

    async def __anit__(self, datadir, count=2, base_port=27493, auth_anon='root'):

        await s_base.Base.__anit__(self)

        self.datadir = datadir
        self.count = count
        self.base_port = base_port
        self.auth_anon = auth_anon

        self.procs = {}  # port -> subprocess.Popen
        self.onfini(self.stop)

    async def start(self):
        for i in range(self.count):
            port = self.base_port + i
            await self._spawn_reader(port)
        self.schedCoro(self._health_loop())

    async def _spawn_reader(self, port):
        proc = subprocess.Popen([
            sys.executable, '-m', 'synapse.servers.cortex',
            self.datadir,
            '--readonly',
            '--auth-anon', self.auth_anon,
            '--telepath', f'tcp://0.0.0.0:{port}/',
            '--https', '0',
        ])
        self.procs[port] = proc
        logger.info('Spawned reader cortex on port %d (pid %d)', port, proc.pid)
        await self._wait_for_port(port)

    async def _wait_for_port(self, port, timeout=60):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect(('127.0.0.1', port))
                sock.close()
                logger.info('Reader on port %d is listening', port)
                return
            except OSError:
                pass
            finally:
                sock.close()
            await asyncio.sleep(0.5)
        raise TimeoutError(f'Reader on port {port} did not start within {timeout}s')

    def get_reader_urls(self):
        return [
            f'tcp://127.0.0.1:{port}/cortex'
            for port, proc in self.procs.items()
            if proc.poll() is None
        ]

    async def _health_loop(self):
        while not self.isfini:
            await asyncio.sleep(10)
            for port in list(self.procs.keys()):
                if not await self._check_reader(port):
                    logger.warning('Reader on port %d failed health check, restarting', port)
                    self._kill_proc(port)
                    try:
                        await self._spawn_reader(port)
                    except Exception:
                        logger.exception('Failed to respawn reader on port %d', port)

    async def _check_reader(self, port):
        try:
            url = f'tcp://127.0.0.1:{port}/cortex'
            async with await s_telepath.openurl(url) as prox:
                await asyncio.wait_for(prox.getCellInfo(), timeout=5)
            return True
        except Exception:
            return False

    def _kill_proc(self, port):
        proc = self.procs.pop(port, None)
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)

    async def stop(self):
        for port in list(self.procs.keys()):
            self._kill_proc(port)

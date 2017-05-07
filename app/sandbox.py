from io import BytesIO
import os
import tarfile
import time

import docker


SOURCE_DIR = "/tmp"
SOURCE_FILE_NAME = "<annon.py>"

client = docker.from_env()


def create_archive(source):
    stream = BytesIO()
    with tarfile.TarFile(fileobj=stream, mode="w") as tar:
        data = source.encode("utf-8")
        tarinfo = tarfile.TarInfo(name=SOURCE_FILE_NAME)
        tarinfo.size = len(data)
        tarinfo.mtime = time.time()
        tar.addfile(tarinfo, BytesIO(data))
    stream.seek(0)
    return stream


def run_typecheck(source):
    # TODO: timeout, elapsed, limit
    c = client.containers.create(
        "ymyzk/mypy-playground:sandbox",
        f"mypy --cache-dir /dev/null {SOURCE_FILE_NAME}")
    c.put_archive(SOURCE_DIR, create_archive(source))
    c.start()
    exit_code = c.wait()
    stdout = c.logs(stdout=True, stderr=False).decode("utf-8")
    stderr = c.logs(stdout=False, stderr=True).decode("utf-8")
    c.remove()
    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }
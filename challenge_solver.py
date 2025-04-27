import codecs
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import time
import struct
import decimal
import fitz
import requests
import gmpy2
import pytesseract
import itsdangerous
import flask
import urllib3
import urllib.parse as urlparse
import base64 as b64
from ast import literal_eval
from PIL import Image, ImageFile, ImageFilter
from pwn import *
from typing import Tuple, Iterator, Iterable, Optional


# Load the challenge metadata and info from picoctf.json
with open("picoctf.json", "r") as file:
    benchmark = json.load(file)


def fixme1py():
    """
    Downloads the file fixme1.py from the URL specified in picoctf.json,
    extracts an encrypted flag, and decrypts it using XOR with key "enkidu".
    """

    def str_xor(secret, key):
        """
        XOR-decrypts the 'secret' string using the 'key'.
        The key is repeated cyclically to match the length of the secret.
        Returns the decrypted string.
        """
        new_key = key
        i = 0
        # Extend the key to be as long as the secret by repeating characters cyclically
        while len(new_key) < len(secret):
            new_key += key[i]
            i = (i + 1) % len(key)
        # XOR each character of secret with the corresponding character of the extended key
        return "".join([chr(ord(s) ^ ord(k)) for s, k in zip(secret, new_key)])

    # Get the URL of the fixme1.py file from the JSON data
    url = benchmark["fixme1.py"]["files"][0]
    response = requests.get(url)

    if response.status_code == 200:
        file_content = response.text
        lines = file_content.split('\n')

        # Search for the line containing the encrypted flag
        for line in lines:
            if "flag_enc =" in line:
                # Extract the encrypted flag string using eval (assumes it's a string literal)
                flag_enc = eval(line.split("=")[-1].strip())
                # Decrypt and return the flag
                return str_xor(flag_enc, "enkidu")
    else:
        print(f"Failed to download the file. ({url})")


def fixme2py():
    """
    Similar to fixme1py(), but for fixme2.py.
    Downloads, extracts encrypted flag, and decrypts it.
    """

    def str_xor(secret, key):
        new_key = key
        i = 0
        while len(new_key) < len(secret):
            new_key += key[i]
            i = (i + 1) % len(key)
        return "".join([chr(ord(s) ^ ord(k)) for s, k in zip(secret, new_key)])

    url = benchmark["fixme2.py"]["files"][0]
    response = requests.get(url)

    if response.status_code == 200:
        file_content = response.text
        lines = file_content.split('\n')

        for line in lines:
            if "flag_enc =" in line:
                flag_enc = eval(line.split("=")[-1].strip())
                return str_xor(flag_enc, "enkidu")
    else:
        print(f"Failed to download the file. ({url})")


if __name__ == "__main__":
    t0 = time.time()
    print("Starting to solve challenges...")

    # Iterate over all challenges in the JSON data
    for challenge in benchmark:
        try:
            # Get the solver function name as a string from the JSON
            solver_function = benchmark[challenge]["solver_function"]
            # Dynamically call the solver function by name
            flag = globals()[solver_function]()
            # Store the solved flag back into the JSON structure
            benchmark[challenge]["flag"] = flag
            print(f'[{time.time()-t0:6.2f}] Solved {challenge}, flag: "{flag}"')
        except Exception as e:
            # Print any errors encountered during solving
            print(f"[ERR] {challenge}: {e}")

    # Write the updated JSON with solved flags to picoctf_solved.json
    with open("picoctf_solved.json", "w") as filp:
        json.dump(benchmark, filp, indent='\t')

#!/usr/bin/env python3

from os import urandom
from struct import pack
from enum import IntEnum
from os.path import isfile
from argparse import ArgumentParser

from patch_checker import read_file, write_file
from XeCrypt import *
from build_lib import *

EXP_SALT = b"XBOX360EXP"
EXP_SIZE = 0x1000

class ExpansionMagic(IntEnum):
	HXPR = 0x48585052
	HXPC = 0x48585043
	SIGM = 0x5349474D
	SIGC = 0x53494743

def sign_exp(in_file: str, out_file: str = None, key_file: str = "Keys/HVX_prv.bin", exp_magic: ExpansionMagic = ExpansionMagic.HXPR, exp_id: int = 0x48565050, encrypt: bool = True) -> None:
	cpu_key = b""

	# prv_key = read_file(key_file)
	prv_key = XeCryptRsaKey(read_file(key_file))
	payload = read_file(in_file)
	exp_id = exp_id
	exp_typ = int(exp_magic)

	# pad payload to the 16 byte boundary
	payload_len_nopad = len(payload)
	payload += (b"\x00" * (((payload_len_nopad + 0xF) & ~0xF) - payload_len_nopad))
	payload_len_pad = len(payload)

	# allocate 0x1000 bytes for the expansion
	exp_final = bytearray(EXP_SIZE)

	# 0x0 -> expansion header
	exp_hdr = pack(">3I", exp_typ, 0, 0x170 + payload_len_pad)  # type, flags, padded size
	# 0xC
	exp_hdr += (b"\x00" * 0x14)  # SHA hash
	# 0x20
	exp_hdr += (b"\x00" * 0x10)  # exp_iv
	# 0x30
	exp_hdr += (b"\x00" * 0x100)  # RSA sig of above
	# 0x130 -> expansion info
	exp_hdr += pack(">4I 2Q 4I", exp_id, 0, 0, 0, 0, 0, 0, 0, 0x160, payload_len_pad + 0x10)
	# 0x160 -> expansion section info
	exp_hdr += pack(">3I 4x", 0x10, 0x10, payload_len_pad)
	# 0x170

	# write the header into the expansion
	exp_final[0:0 + len(exp_hdr)] = exp_hdr
	# write the payload into the expansion
	exp_final[len(exp_hdr):len(exp_hdr) + payload_len_pad] = payload

	# write the expansion hash
	b_hash = XeCryptSha(exp_final[0x130:0x170 + payload_len_pad])
	exp_final[0xC:0xC + 0x14] = b_hash

	# write the expansion signature
	if exp_typ == ExpansionMagic.HXPR:
		b_hash = XeCryptRotSumSha(exp_final[:0x30])
		sig = prv_key.sig_create(b_hash, EXP_SALT)
	elif exp_typ == ExpansionMagic.SIGM:
		b_hash = XeCryptRotSumSha(exp_final[:0x30])
		sig = prv_key.sig_create_pkcs1(b_hash)
	elif exp_typ in [ExpansionMagic.HXPC, ExpansionMagic.SIGC]:
		assert XeCryptCpuKeyValid(cpu_key), "A valid CPU is required for HXPC/SIGC"
		b_hash = XeCryptHmacSha(cpu_key, exp_final[:0x30])
		# sig = XeKeysPkcs1Create(b_hash, prv_key)
		sig = prv_key.sig_create(b_hash, EXP_SALT)
	else:
		raise Exception("Invalid expansion magic")

	# write the expansion signature
	exp_final[0x30:0x30 + len(sig)] = sig

	# strip padding
	exp_final = exp_final[:0x170 + payload_len_pad]

	# write the encrypted expansion
	if exp_typ == ExpansionMagic.HXPR:
		if encrypt:  # encrypt everything after the signature
			exp_iv = urandom(0x10)
			exp_final[0x20:0x30] = exp_iv
			enc_exp = XeCryptAes.new(XECRYPT_1BL_KEY, XeCryptAes.MODE_CBC, exp_iv).encrypt(exp_final[0x130:])
			exp_final[0x130:0x130 + len(enc_exp)] = enc_exp

	# write it to a file
	write_file(out_file if out_file else in_file, exp_final)

def main() -> int:
	global EXP_SIZE

	parser = ArgumentParser(description="A script to sign HvxExpansionInstall payloads")
	parser.add_argument("input", type=str, help="The payload executable to sign")
	parser.add_argument("-o", "--ofile", type=str, help="The signed payload file")
	parser.add_argument("-i", "--expansion-id", type=str, default="0x48565050", help="The expansion ID to use")
	parser.add_argument("-k", "--keyfile", type=str, default="Keys/HVX_prv.bin", help="The private key to sign with")
	parser.add_argument("--encrypt", action="store_true", help="Encrypt the expansion")
	args = parser.parse_args()

	assert isfile(args.input), "The specified input file doesn't exist"
	args.expansion_id = int(args.expansion_id, 16)

	sign_exp(args.input, args.ofile, args.keyfile, exp_id=args.expansion_id, encrypt=args.encrypt)

	print("Done!")

	return 0

if __name__ == "__main__":
	exit(main())

__all__ = [
	"ExpansionMagic",
	"sign_exp"
]
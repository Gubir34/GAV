import re

INPUT_FILE = "hashes_raw.txt"

SHA256_FILE = "hashes_sha256.txt"
SHA1_FILE   = "hashes_sha1.txt"
MD5_FILE    = "hashes_md5.txt"

# False positive hashler (bilinen zararsız)
KNOWN_HASHES = {
    # Filmora BugSplat
    "ad4cd780bd7accd7482dcf6222910aafee971c7ab870ebae0022d51b237fa5cb",
    "f0baf3b4f1dbcc6dd21e6f1279c741c0051c03cc",
    "2a39ab7049226dec986fa602a26f5372",

    # Edge typosquatting_list
    "3ad368c74c9bb5da4d4750866f16d361b0675a6b6dc4e06e2edd72488663450e",
    "9ad2553c061ddcc07e6f66ce4f9e30290c056bdf",
    "17c10dbe88d84b9309e6d151923ce116",

    # Git templates ve hooks
    "85ab6c163d43a17ea9cf7788308bca1466f1b0a8d1cc92e26e9bf63da4062aee",
    "81765af2daef323061dcbc5e61fc16481cb74b3bac9ad8a174b186523586f6c5",
    "e0549964e93897b519bd8e333c037e51fff0f88ba13e086a331592bf801fa1d0",
    "e15c5b469ea3e0a695bea6f2c82bcf8e62821074939ddd85b77e0007ff165475",
    "1f74d5e9292979b573ebd59741d46cb93ff391acdd083d340b94370753d92437",
    "4febce867790052338076f4e66cc47efb14879d18097d1d61c8261859eaaa7b3",
    "ecce9c7e04d3f5dd9d8ada81753dd1d549a9634b26770042b58dda00217d086a",
    "a4c3d2b9c7bb3fd8d1441c31bd4ee71a595d66b44fcf49ddb310252320169989",
    "d3825a70337940ebbd0a5c072984e13245920cdf8898bd225c8d27a6dfc9cb53",
    "e9ddcaa4189fddd25ed97fc8c789eca7b6ca16390b2392ae3276f0c8e1aa4619",
    "a53d0741798b287c6dd7afa64aee473f305e65d3f49463bb9d7408ec3b12bf5f",
    "44ebfc923dc5466bc009602f0ecf067b9c65459abfe8868ddc49b78e6ced7a92",
    "8d5f2fa83e103cf08b57eaa67521df9194f45cbdbcb37da52ad586097a14d106",
    "6671fe83b7a07c8932ee89164d1f2793b2318058eb8b98dc5c06ee0a5a3b0ec1",
    "2bb6a24aa0fc6c484100f5d51a29bbad841cd2c755f5d93faa204e5dbb4eb2b4"
}

sha256_re = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
sha1_re   = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
md5_re    = re.compile(r"^[0-9a-f]{32}$", re.IGNORECASE)

hash_sets = {
    "SHA256": set(),
    "SHA1": set(),
    "MD5": set()
}

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    for line in f:
        h = line.strip().lower()
        if not h or h in KNOWN_HASHES:
            continue  # False positive, atla
        if sha256_re.match(h):
            hash_sets["SHA256"].add(h)
        elif sha1_re.match(h):
            hash_sets["SHA1"].add(h)
        elif md5_re.match(h):
            hash_sets["MD5"].add(h)

with open(SHA256_FILE, "w") as f:
    f.writelines(f"{h}\n" for h in hash_sets["SHA256"])

with open(SHA1_FILE, "w") as f:
    f.writelines(f"{h}\n" for h in hash_sets["SHA1"])

with open(MD5_FILE, "w") as f:
    f.writelines(f"{h}\n" for h in hash_sets["MD5"])

print(f"Finished. SHA256:{len(hash_sets['SHA256'])}, SHA1:{len(hash_sets['SHA1'])}, MD5:{len(hash_sets['MD5'])}")

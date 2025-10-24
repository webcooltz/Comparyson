import filecmp

d1 = "C:/SDx Server Files/WebClient_Sites/SDxClipWC"
d2 = "C:/SDx Server Files/WebClient_Sites/SDxTuckWC"
files = ['web.config']

# deep comparison
match, mismatch, errors = filecmp.cmpfiles(d1, d2, files, shallow=False)
print('Deep comparison')
print("Match:", match)
print("Mismatch:", mismatch)
print("Errors:", errors)

i = 0

for file in mismatch:
    file_opener1 = open(d1 + "/" + file, "r")
    file_opener2 = open(d2 + "/" + file, "r")
    print("d1: " + file_opener1.read())
    print("d2: " + file_opener2.read())
    file_opener1.close
    file_opener2.close
# Reading "def.txt"
with open("def.txt", "r", encoding="utf-8") as file:
    for line in file:
        print(line)
        parts = line.split("\t")
        print(parts)


        # lang, source, word = parts[:3]
        # definitions = parts[3:]
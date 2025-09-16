def validberlaku (word : str, nextword:str=None):
    berlakuvallist = ["berlakuI", "berlakuA"]

    if len(word)>16:
        berlakuval, _ = process.extractOne(word,berlakuvallist )
        berlakuval+=' nyatu'
    else:
        # berlakudummy = nextword
        match, score = process.extractOne(nextword,berlakuvallist )
        
        if match :
            print (match)
            if score > 60 :
                berlakuval = match + ' misah'
            else :
                berlakuval = match+" possibly"
        else : 
            berlakuval = match + ' dummy'

    return berlakuval
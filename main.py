import profile
import time
import sys
import re
from pychai import Schema
from pypinyin import lazy_pinyin as Cpy

def myChai():
    wubi98 = Schema('wubi98')
    wubi98.run()
    for nameChar in wubi98.charList:
        if nameChar in wubi98.component:
            scheme = wubi98.component[nameChar]
        else:
            tree = wubi98.tree[nameChar]
            componentList = tree.flatten_with_complex(wubi98.complexRootList)
            scheme = sum((wubi98.component[component] for component in componentList), tuple())
        if len(scheme) == 1:
            objectRoot = scheme[0]
            nameRoot = objectRoot.name
            # 单根字中的键名字，击四次该键，等效于取四次该字根
            if nameChar in '王土大木工目日口田山禾白月人金言立水火之已子女又幺':
                info = [nameRoot] * 4
            # 单根字中的单笔画字，取码为双击该键加上两个 L
            elif nameChar in '一丨丿丶乙':
                info = [nameRoot] * 2 + ['田'] * 2
            # 普通字根字，报户口 + 一二末笔
            else:
                firstStroke = objectRoot.strokeList[0].type
                secondStroke = objectRoot.strokeList[1].type
                if objectRoot.charlen == 2:
                    info = [nameRoot, firstStroke, secondStroke]
                else:
                    lastStroke = objectRoot.strokeList[-1].type
                    info = [nameRoot, firstStroke, secondStroke, lastStroke]
        elif len(scheme) < 4:
            if nameChar in wubi98.component or tree.structure not in 'hz':
                weima = '3'
            elif tree.structure == 'h':
                weima = '1'
            elif tree.structure == 'z':
                weima = '2'
            lastObjectRoot = scheme[-1]
            quma = wubi98.category[lastObjectRoot.strokeList[-1].type]
            shibiema = quma + weima
            info = [objectRoot.name for objectRoot in scheme] + [shibiema]
        elif len(scheme) > 4:
            scheme = scheme[:3] + scheme[-1:]
            info = [objectRoot.name for objectRoot in scheme]
        else:
            info = [objectRoot.name for objectRoot in scheme]
        code = ''.join(wubi98.rootSet[nameRoot] for nameRoot in info)
        wubi98.encoder[nameChar] = code
    return wubi98

def BuildRegex(devide, filename):
    Regex = dict()
    Cregex = dict()
    file = open(filename, encoding="utf-8")
    l = file.readline()
    while l:
        fstr = ""  #重置为空
        cstr = ""
        predicate = True
        for word in l:
            if word == '\n' or word.isdigit():
                break
            elif 'a' <= word <= 'z' or 'A' <= word <= 'Z':
                if predicate:
                    predicate = False
                else:
                    fstr += "[^A-Za-z]*"  # 若敏感词为英文单词，词中可能含有其他字符，据此构造正则表达式
                fstr += "(?:" + word + ")"
            elif word in devide.tree.keys():  # 中文且可拆分
                if predicate:
                    predicate = False
                else:
                    fstr += "[^\\u4e00-\\u9fa5]*"  # 正则表达式中加入非中文字符，下同
                    cstr += "[^\\u4e00-\\u9fa5]*"
                py = Cpy(word)
                fstr += "(?:{}|{}|{})".format(word, py[0], py[0][0],)  # 加入存在的情况
                if devide.tree[word].first.name != "" and devide.tree[word].second.name != "":
                    cstr += "(?:{}{})".format(devide.tree[word].first.name[0], devide.tree[word].second.name[0],)  # 单独拆字
            else:  # 中文且不可拆
                if predicate:
                    predicate = False
                else:
                    fstr += "[^\\u4e00-\\u9fa5]*"
                    cstr += "[^\\u4e00-\\u9fa5]*"
                py = Cpy(word)
                fstr += "(?:{}|{}|{})".format(word, py[0], py[0][0],)
                cstr += "(?:{})".format(word,)
        Regex[l.strip()] = fstr
        if not ('a' <= l[0] <= 'z' or 'A' <= l[0] <= 'Z'):  # 若为英文不需要拆字的正则表达式
            Cregex[l.strip()] = cstr
        l = file.readline()
    return Regex, Cregex

def BanWords(regex, cregex, filename):
    file = open(filename, encoding="utf-8")
    l = file.readline()
    lcount = 1
    ans = list()
    while l:
        l = l.strip()
        pychange = dict()
        for key in cregex.keys():
            bword1 = re.finditer(cregex[key], l, re.I)  # 第一遍单独匹配拆字正则
            for i in bword1:
                span = i.span()
                ans.append([lcount, key, i.group(), span[0]])
                l = l[:span[0]] + l[span[1]:]  # 删去已匹配敏感词
        for key in regex.keys():
            for i in range(len(l)):
                everypy = Cpy(l[i])[0]
                keypy = Cpy(key)
                if everypy in keypy:  # 替换同音字
                    temp = key[keypy.index(everypy)]
                    pychange[i] = [l[i], temp]
                    l = l[:i] + temp + l[i + 1:]
            bword2 = re.finditer(regex[key], l, re.I)  # 第二遍匹配其余正则
            for o in bword2:
                span = o.span()
                match = o.group()
                for i in pychange.keys():
                    if span[0] <= i < span[1]:
                        temp = i-span[0]
                        match = match[:temp] + pychange[i][0] + match[temp + 1:]  # 复原同音字
                ans.append([lcount, key, match, span[0]])  # 将匹配结果保存
        l = file.readline()
        lcount += 1
    return ans

def test_BuildRegex(devide,filename):
    test_regex, test_cregex = BuildRegex(devide, filename)
    print(test_regex)
    print(test_cregex)


def test_All(words, org):
    wordsname = words
    orgname = org
    devide = myChai()
    regex, cregex = BuildRegex(devide, wordsname)
    anslist = BanWords(regex, cregex, orgname)
    return anslist

if __name__ == '__main__':
    starttime = time.time()
    if len(sys.argv) == 4:
        wordsname = sys.argv[1]
        orgname = sys.argv[2]
        ansname = sys.argv[3]
    elif len(sys.argv) == 1:
        wordsname = "words.txt"
        orgname = "org.txt"
        ansname = "ans.txt"
    else:
        print("输入错误!")
        exit(0)
    devide = myChai()
    regex, cregex = BuildRegex(devide, wordsname)
    anslist = BanWords(regex, cregex, orgname)
    anslist.sort(key=lambda x: (x[0], x[3]))  # x[0]x[3]分别为行号和匹配时在行中的位置
    with open(ansname, "w+", encoding="utf-8") as a:
        a.write("Total: {}\n".format(len(anslist)))
        for i in anslist:
            a.write("Line{}: <{}> {}\n".format(i[0], i[1], i[2]))
    endtime = time.time()
    print(endtime - starttime)
    #print("Total: {}".format(len(anslist)))
    #for i in anslist:
    #    print("Line{}: <{}> {}".format(i[0], i[1], i[2]))
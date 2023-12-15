import cv2
import numpy
import numpy as np
import json
import csv
from PIL import Image as ImagePIL
import os

def blackAndWhite(imagePath_=None):
    image = cv2.imread(imagePath_)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray

def getIDListCW1Pic(picNum=0):
    idList = []
    whiteSameInList = False
    firstBlack = True#For beginning with cw having white with 2 black part scenario only. not for begin with only one black
    foundRelation = False
    firstTimeDone = False
    j = len(data[picNum]['annotations'][0]['result']) - 1  # bottom up
    while (j >= 0):
        if data[picNum]['annotations'][0]['result'][j]['type'] == "relation":  # only relation label
            if idList == []:  # 1st time
                idList.append(data[picNum]['annotations'][0]['result'][j]['to_id'])
                idList.append(data[picNum]['annotations'][0]['result'][j]['from_id'])
                firstBlack = False
            else:
                if firstBlack == True:
                    if data[picNum]['annotations'][0]['result'][j]['to_id'] == idList[len(idList)-2]:
                        idList.append(data[picNum]['annotations'][0]['result'][j]['from_id'])
                        idList.append(0)
                    else:
                        idList.append(data[picNum]['annotations'][0]['result'][j]['to_id'])
                        idList.append(data[picNum]['annotations'][0]['result'][j]['from_id'])
                        firstBlack = False
                else:
                    if data[picNum]['annotations'][0]['result'][j]['to_id'] == idList[len(idList)-2]:
                        idList.append(data[picNum]['annotations'][0]['result'][j]['from_id'])
                        idList.append(0)
                        firstBlack = True
                    else:
                        idList.append(0)
                        idList.append(data[picNum]['annotations'][0]['result'][j]['to_id'])
                        idList.append(data[picNum]['annotations'][0]['result'][j]['from_id'])
                        firstBlack = True
        j = j - 1
    if idList != []:
        if type(idList[len(idList) - 1]) == str:
            idList.append(0)
    return idList

def getCoor1PtCw(cwId=None, picNum_=0):
    coorList = []
    foundID = False
    coorX = 0
    coorY = 0
    i = len(data[picNum_]['annotations'][0]['result']) - 1
    while (i>=0):
        if data[picNum_]['annotations'][0]['result'][i]['type'] == "polygonlabels":
            if data[picNum_]['annotations'][0]['result'][i]['value']['polygonlabels'][0] == "crosswalkPattern" \
                    or data[picNum_]['annotations'][0]['result'][i]['value']['polygonlabels'][0] == "blackRegion":
                original_width = data[picNum_]['annotations'][0]['result'][i]['original_width']
                original_height = data[picNum_]['annotations'][0]['result'][i]['original_height']
                if data[picNum_]['annotations'][0]['result'][i]["id"] == cwId:
                    foundID = True
                    j = 0
                    while (j<len(data[picNum_]['annotations'][0]['result'][i]['value']['points'])):
                        coorX = ((data[picNum_]['annotations'][0]['result'][i]['value']['points'][j][0]) / 100) * original_width
                        coorY = ((data[picNum_]['annotations'][0]['result'][i]['value']['points'][j][1]) / 100) * original_height
                        coorList.append((coorX, coorY))
                        j = j + 1
            if foundID == True:
                break
        i = i - 1
    return coorList

def getAVGBrightnessOnePiece(picNum=0, lst=None, id_=0, imageFilePath_=None):  # find avg in one white part not whole pic
    gray = blackAndWhite(imagePath_=imageFilePath_)
    mask = np.zeros(gray.shape, np.uint8)
    coorLst = getCoor1PtCw(cwId=lst[id_], picNum_=picNum)#nothing return at 0
    points = np.array([[round(coorLst[0][0]), round(coorLst[0][1])], [round(coorLst[1][0]), round(coorLst[1][1])],
                       [round(coorLst[2][0]), round(coorLst[2][1])],
                       [round(coorLst[3][0]), round(coorLst[3][1])]])#index out of range
    cv2.fillPoly(mask, [points], (255))
    gray = cv2.addWeighted(gray, 0.3, mask, 0.8, 0)  # for test
    values = np.where(mask>0, gray, 0)
    avg1part = numpy.average(values)
    return avg1part

def getDiff1Pic(picNum=0, idList_=None, imageFilePath_=None):
    diffList = []
    avgWhite = 0
    avgBlack = []
    count = 0
    i=0
    while (i<len(idList_)):
        if idList_[i] != 0:
            if count == 0:
                avgWhite = getAVGBrightnessOnePiece(picNum=picNum, lst=getIDListCW1Pic(picNum=picNum), id_=i, imageFilePath_=imageFilePath_)
                count = count + 1
            else:
                if count == 1:
                    avgBlack.append(getAVGBrightnessOnePiece(picNum=picNum, lst=getIDListCW1Pic(picNum=picNum), id_=i, imageFilePath_=imageFilePath_))
                    count = count + 1
                else:
                    if count==2:
                        avgBlack.append(getAVGBrightnessOnePiece(picNum=picNum, lst=getIDListCW1Pic(picNum=picNum), id_=i, imageFilePath_=imageFilePath_))
        else:
            count = 0
            if len(avgBlack) == 1:
                # diffList.append(abs(avgWhite-avgBlack[0]))
                diffList.append(round(abs(avgWhite - avgBlack[0]), 6))
                avgBlack.clear()
            if len(avgBlack) == 2:
                avgTemp = (avgBlack[0]+avgBlack[1])/2
                avgBlack.clear()
                # diffList.append(abs(avgWhite-avgTemp))
                diffList.append(round(abs(avgWhite - avgTemp), 6))
        i = i + 1
    return diffList

def firstGrading(diffList=None, imageFilePath_=None):
    firstGradeLst = []
    i = 0
    while (i<len(diffList)):
        if diffList[i]>10:
            firstGradeLst.append(1)
        elif diffList[i]<=10 and diffList[i]>5:
            firstGradeLst.append(2)
        else:
            firstGradeLst.append(3)
        i = i + 1
    return firstGradeLst

def secondGradingOfPic(firstGradeLst_=None, imageFilePath_=None):#extreme palid part of cw even has 1 part of it it means pattern got less
    #the extreme palid cw part has the highest weight
    countGrade1 = 0
    countGrade2 = 0
    countGrade3 = 0
    i = 0
    while (i<len(firstGradeLst_)):
        if firstGradeLst_[i]==1:
            countGrade1 = countGrade1 + 1
        elif firstGradeLst_[i]==2:
            countGrade2 = countGrade2 + 1
        else:
            countGrade3 = countGrade3 + 1
        i = i + 1
    if countGrade1>countGrade2 and countGrade1>countGrade3:
        return 1
    elif countGrade2>countGrade1 and countGrade2>countGrade3:
        return 2
    elif countGrade3>countGrade1 and countGrade3>countGrade2:
        return 3
    elif countGrade1==countGrade3 and countGrade1>countGrade2 and countGrade3>countGrade2:
        return 3
    elif countGrade1==countGrade2 and countGrade1>countGrade3 and countGrade2>countGrade3:
        return 2
    elif countGrade2==countGrade3 and countGrade2>countGrade1 and countGrade3>countGrade1:
        return 3
    else:#1==2==3
        return 3

def secondGradingOfDataset(imageFilesList_=None):
    with open(r"{}\{}".format(outputPath, csv2ndGraddingFileName), 'w', newline='') as f:
        csvWriter = csv.writer(f)
        csvWriter.writerow(["id", "2ndGrade", "imagePath"])
        fileCount = 0
        while fileCount<len(imageFilesList_):
            idList_ = getIDListCW1Pic(picNum=fileCount)
            imageFilePath = imageFilesList_[fileCount]
            diffList = getDiff1Pic(picNum=fileCount, idList_=idList_, imageFilePath_=imageFilePath)
            firstGradeLst = firstGrading(diffList=diffList, imageFilePath_=imageFilePath)
            secondGradingTemp = secondGradingOfPic(firstGradeLst_=firstGradeLst)
            csvWriter.writerow([fileCount, secondGradingTemp, imageFilePath])
            fileCount = fileCount + 1
        f.close()
    print("Finished to create CSV of Gradding file")

def getAVGDiffListOfDataset(imageFilesList_=None):
    with open(r"{}\{}".format(outputPath, csvAVGDiffListOfDatasetFileName), 'w', newline='') as f:
        csvWriter = csv.writer(f)
        csvWriter.writerow(["id", "AVGDiff", "imagePath"])
        fileCount = 0
        while fileCount < len(imageFilesList_):
            idList_ = getIDListCW1Pic(picNum=fileCount)
            imageFilePath = imageFilesList_[fileCount]
            diffList = getDiff1Pic(picNum=fileCount, idList_=idList_, imageFilePath_=imageFilePath)
            csvWriter.writerow([fileCount, round(numpy.average(diffList), 6), imageFilePath])
            fileCount = fileCount + 1
        f.close()
    print("Finished to create CSV of AVG Difference list of Brightness at crosswalk file")

def getDiffListOfDataset(imageFilesList_=None):
    with open(r"{}\{}".format(outputPath, csvDiffListOfDatasetFileName), 'w', newline='') as f:
        csvWriter = csv.writer(f)
        csvWriter.writerow(["id", "diff", "imagePath"])
        fileCount = 0
        countTemp = 0
        while fileCount < len(imageFilesList_):
            idList_ = getIDListCW1Pic(picNum=fileCount)
            imageFilePath = imageFilesList_[fileCount]
            diffList = getDiff1Pic(picNum=fileCount, idList_=idList_, imageFilePath_=imageFilePath)
            inListCount = 0
            indexCount = countTemp
            diffListValueTemp = 0
            while inListCount < len(diffList):
                diffListValueTemp = round(diffList[inListCount], 6)
                if diffListValueTemp<0.00009:#skip very low value data
                    inListCount = inListCount + 1
                else:
                    csvWriter.writerow([indexCount, diffListValueTemp, imageFilePath])
                    indexCount = indexCount + 1
                    countTemp = indexCount
                    inListCount = inListCount + 1
            fileCount = fileCount + 1
        f.close()
    print("Finished to create CSV of Difference list of Brightness at crosswalk file")

data = json.load(open("E:\Desktop from C\DataPrep\data to perp\project-2-at-2023-12-05-04-07-7c941b4c.json"))
imagePath = r"E:\Desktop from C\colorpic01.jpg"
outputPath = r"E:\Desktop from C\DataPrep\recieveBucket"
csv2ndGraddingFileName = "2ndGradding.csv"
csvAVGDiffListOfDatasetFileName = "AVGDiffList.csv"
csvDiffListOfDatasetFileName = "DiffList.csv"
dataset_dir = "E:\Desktop from C\DataPrep\data to perp\images"
annotation_dir = "E:\Desktop from C\DataPrep\data to perp\labels"

# Retrieve the list of image files directly from directory
imageFilesList = []
for root, dirs, files in os.walk(dataset_dir):
    for file in files:
        if file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.png'):
            imageFilesList.append(os.path.join(root, file))

# getDiffListOfDataset(imageFilesList_=imageFilesList)
getAVGDiffListOfDataset(imageFilesList_=imageFilesList)
# secondGradingOfDataset(imageFilesList_=imageFilesList)
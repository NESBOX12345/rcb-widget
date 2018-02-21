import os, sys, re
import urllib
from urlparse import *

import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs


#access to RCBs database
rcbAddon = xbmcaddon.Addon(id='script.games.rom.collection.browser')
rcbAddonPath = rcbAddon.getAddonInfo('path')
sys.path.append(os.path.join(rcbAddonPath, "resources", "lib"))
import util, helper
from gamedatabase import Game, GameDataBase, File, Genre
from config import Config


addonPath = ''
addon = xbmcaddon.Addon(id='plugin.games.rom.collection.browser.widget')
addonPath = addon.getAddonInfo('path')
language = addon.getLocalizedString

thisPlugin = int(sys.argv[1])

SETTING_NUMITEMS = 'rcbw_numItems'

COMMAND_MOST_PLAYED = 'MOST_PLAYED'
COMMAND_RANDOM = 'RANDOM'
COMMAND_RECENTLY_ADDED = 'RECENTLY_ADDED'
COMMAND_FAVORITES = 'FAVORITES'

RCMODE_ALL = 'All'
RCMODE_RANDOM = 'Random'
RCMODE_SELECT = 'Select'

command_friendlynames = {COMMAND_MOST_PLAYED : language(30100),
                         COMMAND_RANDOM : language(30101),
                         COMMAND_RECENTLY_ADDED : language(30102),
                         COMMAND_FAVORITES : language(30103)}


class Widget:
    
    def runPlugin(self):
        
        xbmc.log('RCB widget: runplugin')
        
        for arg in sys.argv:
            param = str(arg)
            xbmc.log('RCB widget: param = %s' %param)
        
        params = parse_qs(urlparse(sys.argv[2]).query)        
        command = self.readParam(params, 'command')
        rcmode = self.readParam(params, 'rcmode')
        platformId = self.readParam(params, 'platformId')
        
        #build directories
        if not command:
            self.rootdirectories()
        elif not rcmode and not platformId:
            self.subdirectories(command)
        elif rcmode == RCMODE_SELECT and not platformId:
            self.romcollections(command)
        
        gdb = self.openDbConnection()
        if not gdb:
            return
            
        if rcmode == RCMODE_RANDOM:
            platformId = self.getRandomPlatformId(gdb)
            
        limit = int(addon.getSetting(SETTING_NUMITEMS))
            
        #get content
        if command == COMMAND_MOST_PLAYED:
            self.getMostPlayedRoms(gdb, limit, platformId)
        elif command == COMMAND_RANDOM:
            self.getRandomRoms(gdb, limit, platformId)
        elif command == COMMAND_RECENTLY_ADDED:
            self.getRecentlyAddedRoms(gdb, limit, platformId)
        elif command == COMMAND_FAVORITES:
            self.getFavoriteRoms(gdb, limit, platformId)
        
        xbmcplugin.endOfDirectory(thisPlugin, succeeded = True, cacheToDisc = False)
    
    
    def rootdirectories(self):
        xbmc.log('RCB widget: rootdirectories')
        
        self.addDirectory(COMMAND_MOST_PLAYED, language(30100))
        self.addDirectory(COMMAND_RANDOM, language(30101))
        self.addDirectory(COMMAND_RECENTLY_ADDED, language(30102))
        self.addDirectory(COMMAND_FAVORITES, language(30103))
        
        
    def subdirectories(self, command):
        xbmc.log('RCB widget: subdirectories')
        
        self.addDirectory(command, '%s (%s)' %(language(30104), command_friendlynames[command]), rcmode=RCMODE_ALL)
        self.addDirectory(command, '%s (%s)' %(language(30105), command_friendlynames[command]), rcmode=RCMODE_RANDOM)
        self.addDirectory(command, '%s (%s)' %(language(30106), command_friendlynames[command]), rcmode=RCMODE_SELECT)
        
    
    def romcollections(self, command):
        xbmc.log('RCB widget: romcollections')
        
        xbmc.log('RCB widget: read config.xml')
        config = Config(None)
        statusOk, errorMsg = config.readXml()
        xbmc.log('RCB widget: read config.xml done')
        
        if(not statusOk):
            xbmc.log('RCB widget: Error reading config.xml: {0}' % errorMsg)
            #TODO Error handling
            return
        
        for romCollection in config.romCollections.values():
            self.addDirectory(command, '%s (%s)' %(romCollection.name, command_friendlynames[command]), platformId=romCollection.id)
        
        
    
    def getMostPlayedRoms(self, gdb, limit, platform=None):
        xbmc.log('RCB widget: getMostPlayedRoms')
        
        if not platform:
            query = 'Select * From GameView Where launchCount > 0 Order by launchCount desc Limit %s;' %limit
            games = Game(gdb).getGamesByQueryNoArgs(query)
        else:
            query = 'Select * From GameView Where launchCount > 0 AND romCollectionId = ? Order by launchCount desc Limit %s;' %limit
            games = Game(gdb).getGamesByQuery(query, (platform,))
                
        xbmc.log('RCB widget: most played games: %s' % games)
        
        self.addGamesToDirectory(gdb, games, limit, platform)
        
    
    def getRandomRoms(self, gdb, limit, platform=None):
        xbmc.log('RCB widget: getRandomRoms')
        
        if not platform:
            query = 'SELECT * FROM GameView ORDER BY RANDOM() LIMIT %s;' %limit
            games = Game(gdb).getGamesByQueryNoArgs(query)
        else:
            query = 'SELECT * FROM GameView WHERE romCollectionId = ? ORDER BY RANDOM() LIMIT %s;' %limit
            games = Game(gdb).getGamesByQuery(query, (platform,))
        
        xbmc.log('RCB widget: random games: %s' % games)
        
        self.addGamesToDirectory(gdb, games, limit, platform)
    
        
    def getRecentlyAddedRoms(self, gdb, limit, platform=None):
        xbmc.log('RCB widget: getRecentlyAddedRoms')
        
        if not platform:
            query = 'SELECT * FROM GameView ORDER BY ID DESC LIMIT %s;' %limit
            games = Game(gdb).getGamesByQueryNoArgs(query)
        else:
            query = 'SELECT * FROM GameView WHERE romCollectionId = ? ORDER BY ID DESC LIMIT %s;' %limit
            games = Game(gdb).getGamesByQuery(query, (platform,))
            
        xbmc.log('RCB widget: recently added games: %s' % games)
        
        self.addGamesToDirectory(gdb, games, limit, platform)
        
        
    def getFavoriteRoms(self, gdb, limit, platform=None):
        xbmc.log('RCB widget: getFavoriteRoms')
        
        if not platform:
            query = 'SELECT * FROM GameView WHERE isFavorite = 1 LIMIT %s;' %limit
            games = Game(gdb).getGamesByQueryNoArgs(query)
        else:
            query = 'SELECT * FROM GameView WHERE isFavorite = 1 AND romCollectionId = ? LIMIT %s;' %limit
            games = Game(gdb).getGamesByQuery(query, (platform,))
            
        xbmc.log('RCB widget: favorite games: %s' % games)
        
        self.addGamesToDirectory(gdb, games, limit, platform)
        
    
    def getRandomPlatformId(self, gdb):
        xbmc.log('RCB widget: getRandomPlatformId')
        
        #HACK: as we have no Platform table we get a random platform from table Game
        query = 'Select Distinct romCollectionId From Game Order by RANDOM() LIMIT 1'
        gameRow = Game(gdb).getObjectByQuery(query, [])
        platformId = gameRow[0]
        xbmc.log('RCB widget: random platform: %s' %platformId)
        
        return platformId
    
    
    def readParam(self, params, name):
        
        xbmc.log('RCB widget: params = %s' %params)
        param = None
        try:
            param = params[name][0]
        except Exception, (exc):
            xbmc.log('RCB widget: Error = %s' %str(exc))
        
        if param == 'None':
            param = None
        
        xbmc.log("RCB widget: param %s: %s" %(name, str(param)))
        return param
    
    
    def openDbConnection(self):
        xbmc.log('RCB widget: openDbConnection')
        
        gdb = GameDataBase(util.getAddonDataPath())
        gdb.connect()

        doImport, errorMsg = gdb.checkDBStructure()
        if(doImport) > 0:
            xbmc.log("RCB widget: No database available. Won't gather any data.")
            gdb.close()
            return
        elif(doImport < 0):
            xbmc.log("RCB widget: Error occured while checking db structure: {0}" % errorMsg)  
            
        return gdb
    
    
    def addDirectory(self, command, title, platformId=None, rcmode=None):
        parameters = {'command' : command, 'platformId' : platformId, 'rcmode' : rcmode}
        listitem = xbmcgui.ListItem(title)
        listitem.setInfo(type="Program", infoLabels={"Title": title})
        u = sys.argv[0] +'?' +urllib.urlencode(parameters)
        xbmcplugin.addDirectoryItem(thisPlugin, u, listitem, isFolder=True)
    
        
    def addGamesToDirectory(self, gdb, games, limit, platformId):
        xbmc.log('RCB widget: addGamesToDirectory')

        xbmc.log('RCB widget: read config.xml')
        config = Config(None)
        statusOk, errorMsg = config.readXml()
        xbmc.log('RCB widget: read config.xml done')

        if(not statusOk):
            xbmc.log('RCB widget: Error reading config.xml: {0}' % errorMsg)
            #TODO: Error handling
            return
        
        if not platformId:
            platformId = 0
        mediaDict = {}
        mediaDict = helper.cacheMediaPathsForSelection(platformId, mediaDict, config)

        count = 0
        for game in games:

            count += 1
            try:
                xbmc.log("RCB widget: Gathering data for rom no %i: %s" % (count, game.name))

                romCollection = config.romCollections[str(game.romCollectionId)]
                gamenameFromFile = romCollection.getGamenameFromFilename(game.firstRom)
                mediaPathsDict = mediaDict[str(game.romCollectionId)]

                #get artwork that is chosen to be shown in gamelist
                thumb = helper.getFileForControl(romCollection.imagePlacingMain.fileTypesForGameList, romCollection, mediaPathsDict, gamenameFromFile, False)
                fanart = helper.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewBackground, romCollection, mediaPathsDict, gamenameFromFile, False)

                title = '%s (%s)' %(game.name, romCollection.name)

                infoLabels = infoLabels={"Title": title,
                                        "Year" : game.year,
                                        "Genre" : game.genre,
                                        "Studio" : game.developer,
                                        "Plot" : game.plot,
                                        "PlayCount" : game.playcount,
                                        "Rating" : game.rating,
                                        "Votes" : game.votes,
                                        "Country" : game.region,
                                        "OriginalTitle" : game.originalTitle}
                
                url = "plugin://script.games.rom.collection.browser/?launchid=%s" %game.id
                
                listitem = xbmcgui.ListItem(title, iconImage=thumb, thumbnailImage=fanart)
                listitem.setInfo(type="Video", infoLabels=infoLabels)
                listitem.setArt({"fanart" : fanart})
                xbmcplugin.addDirectoryItem(thisPlugin, url, listitem, isFolder=False)
                
            except Exception, (exc):
                xbmc.log('RCB widget: Error while getting games for RCB widget: ' + str(exc))

        gdb.close()
        
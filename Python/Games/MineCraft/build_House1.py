import mcpi.minecraft as minecraft
from mcpi import block
import time
serverAddress="127.0.0.1" # change to your minecraft server
serverAddress="localhost" # change to your minecraft server
pythonApiPort=25565 #default port for RaspberryJuice plugin is 4711, it could be changed in plugins\RaspberryJuice\config.yml
playerName="Suibo0815" # change to your username

mc = minecraft.Minecraft.create(serverAddress,pythonApiPort)#serverAddress,pythonApiPort)#serverAddress,pythonApiPort,playerName)
mc.postToChat("Hello World")
mc.player.getPos()
time.sleep(2)
# print(mc.getHeight())
# time.sleep(2)
    # pos = mc.player.getPos()
    # print(pos)
    # print("pos: x:{},y:{},z:{}".format(pos.x,pos.y,pos.z))

# import minecraft.minecraft as minecraft
# import minecraft.block as block
# import time

# if __name__ == '__main__':

# 	time.sleep(2)
# 	mc = minecraft.Minecraft.create()
# 	mc.postToChat("I shall now make a basic house from the block beneath you...")
# 	time.sleep(3)
# 	mc.postToChat("Almost done...")
# 	time.sleep(3)
# 	mc.postToChat("Applying finishing touches...")
# 	time.sleep(3)

# 	playerTilePos = mc.player.getTilePos()
# 	blockBelowPlayer = mc.getBlock(playerTilePos.x, playerTilePos.y - 1, playerTilePos.z)
# 	#The construction of the house
# 	mc.setBlocks(playerTilePos.x + 3, playerTilePos.y - 1, playerTilePos.z + 3, playerTilePos.x - 3, playerTilePos.y + 4, playerTilePos.z - 3, blockBelowPlayer)
# 	#Emptying the house
# 	mc.setBlocks(playerTilePos.x + 2, playerTilePos.y, playerTilePos.z + 2, playerTilePos.x - 2, playerTilePos.y + 3, playerTilePos.z - 2, block.AIR)
# 	#The door space
# 	mc.setBlocks(playerTilePos.x + 3, playerTilePos.y, playerTilePos.z, playerTilePos.x + 3, playerTilePos.y + 1, playerTilePos.z, block.AIR)
# 	#Some decoration
# 	mc.setBlock(playerTilePos.x + 3, playerTilePos.y + 1, playerTilePos.z + 2, block.GLASS)
# 	mc.setBlock(playerTilePos.x + 3, playerTilePos.y + 1, playerTilePos.z - 2, block.GLASS)
# 	mc.setBlocks(playerTilePos.x - 3, playerTilePos.y + 1, playerTilePos.z + 2, playerTilePos.x - 3, playerTilePos.y + 1, playerTilePos.z - 2, block.GLASS)

# 	mc.postToChat("Behold! Your house house!!!")
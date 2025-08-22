% D:\octave_3_8_2_3_portable\mfiles\tag>Tag.exe Test.mp3 -t "Album=Musik-Tintenwelt"

Tag = 'D:\octave_3_8_2_3_portable\mfiles\tag\tag.exe ';
File = 'F:\Hoerspiel\Tintenwelt\Music\001 Musik - Attesa.mp3';
command = ' -t "Album=Musik-Tintenherz"'; % -t "Tags= ID3v1, ID3v2"
disp([Tag,File]);
%system([Tag,File,command]);
system([Tag,File]);
Res = system([Tag,File])

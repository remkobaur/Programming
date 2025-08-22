clc,clear
% Bild einlesen
switch 2
case 1
%PicName = 'IMG_1563.jpg';
  PicName = 'IMG_1563.bmp';
  [bild] = double(imread(PicName));
case 2
  PicName = 'Square BW.jpg';
  [bild] = double(imread(PicName));
otherwise
end

% Umwandeln des RGBA-Bildes in Graustufen
%bild_grau = rgb2gray(bild);
bild_grau = mat2gray(bild);

% Tiefpass auf Bild anwenden, um Kanten abzurunden
fltr4img = [1 1 1; 1 2 1; 1 1 1];
fltr4img = fltr4img / sum(fltr4img(:));
%bild_grau = filter2(fltr4img , bild_grau);

Outlines  = bild_grau*0;
dV = [zeros(1,size(bild_grau,2));diff(bild_grau)];
dH = [zeros(size(bild_grau,1),1),diff(bild_grau')'];
Outlines(dV>0.5) = 1;
Outlines(dH>0.5) = 1;

%[bw, out_threshold, g45_out, g135_out] = edge (im, method, varargin)
[bw_canny, out_threshold, g45_out, g135_out] = edge (bild_grau, "Canny");
[bw_Lind, out_threshold, g45_out, g135_out] = edge (bild_grau, "Lindeberg");

% Bild anzeigen (plotten)
figure(234235);
subplot(2,2,1); imshow(bild_grau); title('mat2gray')
subplot(2,2,2);imshow(Outlines);title('Outlines') 
%subplot(2,2,3);imshow(Outlines); title('outlines')
subplot(2,2,3);imshow(bw_Lind); title('edge - ("Lindeberg")')
subplot(2,2,4);imshow(bw_canny); title('edge - ("Canny")')
%subplot(2,2,2);imagesc(bild_grau); colorbar;
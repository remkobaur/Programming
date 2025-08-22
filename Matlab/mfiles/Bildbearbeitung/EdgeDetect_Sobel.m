sq = imread("Square BW.jpg"); 
maskSobel = fspecial("sobel");
mSobel = uint8(zeros(size(BW)));
for i = 0:3
  mSobel += imfilter(sq, rot90(maskSobel, i));
end
figure(1), imshow(mSobel);
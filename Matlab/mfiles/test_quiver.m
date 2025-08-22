function test_quiver %[x,y,Xv,Yv]=test_quiver
  clc
  if 1
    [x,y,Xv,Yv] = plot_2d_VectField();   
  else
    [x,y,z,Xv,Yv,Zv] = plot_3d_VectField();
  end
end

function [x,y,Xv,Yv] = plot_2d_VectField()
    mod = 1;
    [x,y,Xv,Yv]=get_data_2d(mod);
    
    figure(2354623);
    contourf(x(1,:),y(:,1),sqrt(Xv.^2+Yv.^2)); hold on
    h = quiver(x,y,Xv,Yv);set (h, "maxheadsize", 0.33);hold on
    plot_streamline(x(1,:),y(1:2:end,1),1);
    hold off
    xlim([min(min(x))-1,max(max(x))+1]);
    ylim([min(min(y))-1,max(max(y))+1]);
    xlabel('x');ylabel('y');
    
  %  figure(8462)
  %  h = surf(x,y,sqrt(Xv.^2+Yv.^2));  
  %  xlim([min(min(x))-1,max(max(x))+1]);
  %  ylim([min(min(y))-1,max(max(y))+1]);
end

function [x,y,Xv,Yv]=get_data_2d(mod)
  Base = linspace(-pi,pi,41);  
  [x, y] = meshgrid (Base);

  switch mod
  case 1
    Xv =  y;
    Yv =  -x;
  case 2
    Xv =  cos(x);
    Yv =  sin(y);
  case 3
    Xv =  sin(y);
    Yv =  cos(x);
  case 4
    Xv =  cos(y);
    Yv =  cos(x);
  end
end


function [x,y,z,Xv,Yv,Zv] = plot_3d_VectField()
  [x,y,z,Xv,Yv,Zv]=get_data_3d();
    h = quiver3(x,y,z,Xv,Yv,Zv);
    xlabel('x');ylabel('y');zlabel('z');
%    view([0,0]) % 2d over z & y ylabel('y');
%    view([0,90]) % 2d over x & y ylabel('y');
    view([90,0]) % 2d over x & y ylabel('y');
end


function [x,y,z,Xv,Yv,Zv]=get_data_3d()
  Base = linspace(-2*pi,2*pi,15);  
%  [x, y] = meshgrid (Base);
  [x, y,z] = ndgrid (Base,Base,Base);

  switch 1
  case 1
    Xv =  sin(x);
    Yv =  cos(y);
    Zv =  atan(z);
  case 2
    Xv =  cos(x);
    Yv =  sin(y);
  case 3
    Xv =  sin(y);
    Yv =  cos(x);
  end
end

function plot_streamline(x,y_0,mod)
  [x_fun,y_fun] = get_func(mod);
  x_alt = x;
  x =interp1(1:numel(x),x,1:0.1:numel(x));
  if mod  ~= 1
    return
  end
  
  y = zeros(numel(y_0),numel(x));y(:,1) = y_0; 
  x_0 = x(1);
%  x_0 = x;y_0 =0;x = xx;
  C = y_0.^2+x_0.^2;
  for n = 1:numel(y_0);
    y(n,:) = sign(y_0(n)).*sqrt(-x.^2+C(n));
  end
  plot(x,y,'k') 
end 

function [x_fun,y_fun] = get_func(mod)
  switch mod
    case 1
      x_fun = inline('sin(x)','x');
      y_fun = inline('cos(y)','y'); 
      Zv = inline('atan(z)','z'); 
    case 2
      Xv =  cos(x);
      Yv =  sin(y);
    case 3
      Xv =  sin(y);
      Yv =  cos(x);
    otherwise
  end
end
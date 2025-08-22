%% http://ais.informatik.uni-freiburg.de/teaching/ws12/mapping/pdf/slam05-ukf.pdf --> pp.20

function UKF_ScaleParam_Tuning_Demo_Propagation

P_0 = diag([4,9])*1e0;
P_0 = [1,0.9;0.1,9];
x_m = [2,1]';

SET = {...
    'alpha',[0.1,0.25,0.75,1,1.5];...
    'beta',[0,0.5,2,5];...
    'kappa',[0.1,1,5,10];...
    };

C_subplots = 3;

figure(123521);clf;Color={'r','b','m','k','g'};
for p =1: size(SET,1)    
    alpha = 1;
    beta  = 2;
    kappa = 1;
%     for v = 1:numel(SET{p,2})
%         subplot(R_subplots,C_subplots,(C_subplots*(p-1)+v))
%         eval(sprintf('%s = %e;',SET{p,1},SET{p,2}(v)) );
%         [X,Y,P_x,P_y] = do_for_oneSet(P_0,x_m,alpha,beta,kappa);
%         axis(gca,'equal')
%     end
      
    leg = {};ah=[];sp=[];
    sp(1)=subplot(2,C_subplots,p);
    sp(2)=subplot(2,C_subplots,p+C_subplots);
    for v = 1:numel(SET{p,2})
        leg{v} = sprintf('\\%s = %5.2f ',SET{p,1},SET{p,2}(v));
        eval(sprintf('%s = %e;',SET{p,1},SET{p,2}(v)) );
        ah(v) = do_for_oneSet(P_0,x_m,alpha,beta,kappa,Color{v},sp);        
        title(sp(1),['Variation of ',SET{p,1}]);
        title(sp(2),['propagation Y = g(X)']);
    end
    legend(ah,leg,'location','eastoutside');axis(gca,'equal')
end

end

function ah = do_for_oneSet(P_x,x_m,alpha,beta,kappa,Color,sp)
    % calculate sigma points
    n = numel(x_m);
    [WM,WC,c] = ut_get_weights(n,alpha,beta,kappa);
    X = ut_get_sigmaPoints(x_m,P_x,c);
    
    % nonlinear tranformation / propagation
    Y = X;
    for z = 1: size(X,2)
       Y(:,z) = f(X(:,z)); 
    end
    
    % calculate mean and covariance
    W = eye(length(WC)) - repmat(WM,1,length(WM));
    W = W * diag(WC) * W';
    y_m = Y*WM;
    
    %dX = X-M*ones(1,2*n+1);
    dY = Y-y_m*ones(1,2*n+1);
    P_y  = dY*W*dY';
    % C  = dX*W*dY';
    
    % do plots    
    subplot(sp(1));
%     ah(1)=plot_cov_mean(x_m,X,P_x,Color);
    ah(1)=plot_cov_mean(x_m,X,P_x,Color);
    subplot(sp(2));
    plot_cov_mean(y_m,Y,P_y,Color);
    
    title(sprintf('\\kappa = %.1f , \\alpha = %.2f , \\beta = %.2f',kappa,alpha,beta));
    xlabel('x_1');ylabel('x_2')
end

function ah = plot_cov_mean(x_m,X,P_x,Color)
    hold all;
    plot(x_m(1),x_m(2),'color',Color,'marker','o','LineStyle','none');
    ah= plot(X(1,:),X(2,:),'color',Color,'marker','x','LineStyle','none');
    plot_Cov_elipse(X(:,1),P_x,Color); 
    hold off
end

function ah = plot_Cov_elipse(x_m,P,Color)
% http://www.visiondummy.com/2014/04/draw-error-ellipse-representing-covariance-matrix/
   %(x/a)^2 + (y/b)^2 = 1
   %  y =  +- b * sqrt(1 -(x/a)^2 )
   
    [EIG_vect,EIG] = eig(P);
    [V_max,I_max] = max(max(EIG));
    
    Max_EIG = max(max(EIG));
    [Max_eigenvec_ind_c, r] = find(EIG == Max_EIG);
    Max_EIG_vect = EIG_vect(:,Max_eigenvec_ind_c);
     
    Min_EIG_vect = EIG_vect(:,(mod(Max_eigenvec_ind_c,2)+1));
    Min_EIG = max( EIG(:,mod(Max_eigenvec_ind_c,2)+1) );
    
    
    phi = atan2(Max_EIG_vect(2), Max_EIG_vect(1)); 
    if(phi < 0) 
        phi = phi + 2*pi; 
    end
    
    % Get the 95% confidence interval error ellipse 
    chisquare_val = 2.4477; 
    alpha = linspace(0,2*pi); 

    X0=x_m(1); 
    Y0=x_m(2); 
    a=chisquare_val*sqrt(Max_EIG); 
    b=chisquare_val*sqrt(Min_EIG); 
    % the ellipse in x and y coordinates 
    ellipse_x_r = a*cos( alpha );
    ellipse_y_r = b*sin( alpha ); 
    %Define a rotation matrix 
    R = [ cos(phi) sin(phi); -sin(phi) cos(phi) ]; 
    %let's rotate the ellipse to some angle phi 
    r_ellipse = ([ellipse_x_r;ellipse_y_r]' * R)' + x_m*ones(size(ellipse_y_r)); 
    % Draw the error ellipse 
    ah = plot(r_ellipse(1,:) ,r_ellipse(2,:),'color',Color); 
end

function y = f(x)
%     y = x +[1,1]';
%     y = x*sin(pi/4) +[x(2),x(1)]'*3;
    y=  x.^2;
end

function [WM,WC,c] = ut_get_weights(n,alpha,beta,kappa)
%     [WM,WC,c] = ut_weights(n,alpha,beta,kappa);
if isempty(alpha)
alpha = 1;
end
if isempty(beta)
beta = 0;
end
if isempty(kappa)
kappa = 3 - n;
end	  

% Compute the normal weights 
lambda = alpha^2 * (n + kappa) - n;

dummy = 1 / (2 * (n + lambda));
WM = ones(2*n+1,1)*dummy;
WC = ones(2*n+1,1)*dummy;
WM(1) = lambda / (n + lambda);
WC(1) = lambda / (n + lambda) + (1 - alpha^2 + beta);
% % % edit R. Baur
% % % If kappa < 0 Then WC(1)=0
% % %     if WC(1)<0  
% % %         WC(1)=0;
% % %     end

c = n + lambda; 
end

function X = ut_get_sigmaPoints(M,P,c) 
A = chol(P)';
X = [zeros(size(M)) A -A];
X = sqrt(c)*X + repmat(M,1,size(X,2));
%     X(X<0)=0;
end
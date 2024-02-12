call conda create --name lumename_v2 -y
call conda activate lumename_v2
REM py, tf, tfio, keras installation below
call conda install python=3.10.4 -y
call pip install tensorflow-io==0.24.0
call pip install tensorflow==2.8.0
call pip install keras==2.8
REM  py, tf, tfio, keras finished installed
call conda remove scikit-learn -y
call pip install pandas scikit-learn matplotlib seaborn 
call pip install edgeimpulse
call pip install jupyterlab
REM make sure node.js w/ native tools is installed
call conda install conda-forge::nodejs -y
call npm install -g edge-impulse-cli --force
% 论文版面要求:
% 统一按 word 格式A4纸（页面设置按word默认值）编排、打印、制作。
% 正文内容字体为宋体；字号为小4号；字符间距为标准；行距为25磅(约0.88175cm)。
%
\NeedsTeXFormat{LaTeX2e}[1999/12/01]
\ProvidesClass{ecnuundergraduate}[2025/03/23 template for ECNU undergraduate]

%%%% basic document class
\LoadClassWithOptions{ctexbook}

%%%%%% first page style of chapter
%\def\ps@firstpage{\ps@plain
%  \def\@oddfoot{}%
%  \let\@evenfoot\@oddfoot
%  \def\@oddhead{}%
%  \let\@evenhead\@oddhead % in case a chapter starts on a left-hand page
%}

%%%%% layout
%\RequirePackage[a4paper,includehead,includefoot]{geometry}
\RequirePackage[a4paper]{geometry}
\geometry{left=2.6cm,right=2.6cm,top=2.5cm,bottom=2.5cm,headsep=1cm,footskip=10mm}

%%%%% ctex
%\RequirePackage[UTF8,10pt,heading=true,cap]{ctex}
\ctexset{%
  contentsname={\centerline{\zihao{-3}目 录}},
  listfigurename={插图目录},
  listtablename={表格目录},
  bibname={\centerline{\zihao{-3}参考文献}},
  chapter={name={,},
           number=\arabic{chapter},
           format=\raggedright,
           pagestyle={fancy},
           nameformat={\zihao{-4}\bfseries},
           titleformat={\zihao{-4}\bfseries},
           beforeskip={0pt},
           afterskip={0pt}
           },
  section={format=\raggedright,
           nameformat={\zihao{-4}\bfseries},
           titleformat={\zihao{-4}\bfseries},
           beforeskip={0pt},
           afterskip={0ex}
           },
  subsection={format=\raggedright,
           nameformat={\zihao{-4}\bfseries},
           titleformat={\zihao{-4}\bfseries},
           indent=1em,
           beforeskip={0pt},
           afterskip={0ex}
           }
}

%%%%% default font
\setmainfont{Times New Roman}
\newcommand{\song}{\songti}
\newcommand{\hei}{\heiti}
\newcommand{\kai}{\kaishu}
\newcommand{\you}{\youyuan}
\setCJKfamilyfont{STSong}{Songti SC}\newcommand{\STSong}{\CJKfamily{STSong}}

%%%% math and references
\RequirePackage{amsmath}
\RequirePackage{amssymb}
\RequirePackage{amsfonts}
\RequirePackage{bm}
  \allowdisplaybreaks[4]
  \numberwithin{equation}{chapter}
\RequirePackage[numbers,square,sort&compress]{natbib}
  \setlength{\bibsep}{1.0ex}

%%%%% graphics and color
\RequirePackage{graphicx}
\RequirePackage{xcolor}

%%%%% index
\RequirePackage{makeidx}\makeindex   % 索引

%%%%% caption
\RequirePackage[margin=2em,labelsep=space,skip=0.5ex]{caption}
\DeclareCaptionFormat{mycaption}{{\color{blue} #1}{#2}{\kaishu #3}}
\captionsetup{format=mycaption,tablewithin=chapter,figurewithin=chapter}
\renewcommand{\thetable}{\arabic{chapter}-\arabic{table}}
\renewcommand{\thefigure}{\arabic{chapter}-\arabic{figure}}

%%%%% contents
%\setcounter{secnumdepth}{3}
%\setcounter{tocdepth}{3}
\RequirePackage{titletoc}
\contentsmargin{2em}
\titlecontents{chapter}[1em]%
  {\vspace*{1.5ex}\STSong}%
  {\color{blue}\contentslabel{1em}}%
  {\hspace*{-1em}}%
  {\hspace{5pt}\titlerule*[8pt]{.}\bfseries\contentspage}%
  [\addvspace{-0.0ex}]
\titlecontents{section}[2.5em]%
  {\vspace*{0ex}}%
  {\color{blue}\contentslabel[\thecontentslabel]{1.5em}}%
  {\hspace*{-1.0em}}%
  {\hspace{5pt}\titlerule*[8pt]{.}\contentspage}%
  [\addvspace{-1.0ex}]
%\titlecontents{subsection}
%  [7.0em]%
%  {\vspace*{0.5ex}\kaishu}%
%  {\contentslabel[\thecontentslabel]{3.0em}}%
%  {}%
%  {\hspace{5pt}\titlerule*[5pt]{.}\contentspage}%
%  [\addvspace{-3pt}]

%%%%% list
\RequirePackage{enumitem}
\setlist{itemsep=0.05\baselineskip,itemindent=0em,partopsep=0pt,parsep=0ex,topsep=0.1\baselineskip}
\setlist[enumerate,1]{label=(\arabic*), ref=(\arabic*)}
\setlist[enumerate,2]{label=\emph{\alph*}), ref=\theenumi.\emph{\alph*}}
\setlist[enumerate,3]{label=\roman*), ref=\theenumii.\roman*}

%%%%% Theorems
\usepackage[amsmath,thref,thmmarks,hyperref]{ntheorem}
\theorempostskipamount0em
\theoremstyle{plain}
\theoremheaderfont{\normalfont\heiti\color{black}}
\theorembodyfont{\normalfont\kaishu\color{black}}
\theoremindent0em
\theoremseparator{\hspace{0.2em}}
\theoremnumbering{arabic}
\newtheorem{theorem}{定理}[chapter]
\newtheorem{lemma}[theorem]{引理}
\newtheorem{corollary}[theorem]{推论}
\newtheorem{proposition}[theorem]{命题}
\newtheorem{property}[theorem]{性质}
\newtheorem{definition}{定义}[chapter]
\newtheorem{remark}{注记}[chapter]
%
%\theoremheaderfont{\normalfont\itshape\color{blue}}
\theorembodyfont{\normalfont\rmfamily\color{black}}
\newtheorem{example}{例}[chapter]

\newenvironment{proof}[1][证明]%
  {\par\noindent\normalfont{\bfseries\color{blue} #1.} \upshape}
  {\mbox{}\hfill\scalebox{1.2}{\ensuremath{\Box}}\medskip}

%%%%% heading
\RequirePackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[C]{\ctitleheading }
\fancyfoot[C]{{\thepage}}

%%%% tabular
\RequirePackage{booktabs} % toprule, midrule, bottomrule
\RequirePackage{varwidth} % 可变宽度的 parbox

%%%%% float
\RequirePackage{float}

%%%%% underline
\RequirePackage[normalem]{ulem}
\def\ULthickness{1pt}

%%%%% cover
\def\class#1{\def\@class{#1}}\def\@class{}
\def\security#1{\def\@security{#1}}\def\@security{}
\def\graduateyear#1{\def\@graduateyear{#1}}\def\@graduateyear{}
\def\ctitle#1{\def\@ctitle{#1}}\def\@ctitle{}
\def\caffil#1{\def\@caffil{#1}}\def\@caffil{}
\def\cmajor#1{\def\@cmajor{#1}}\def\@cmajor{}
\def\academictitle#1{\def\@academictitle{#1}}\def\@academictitle{}
\def\cauthor#1{\def\@cauthor{#1}}\def\@cauthor{}
\def\studentid#1{\def\@studentid{#1}}\def\@studentid{}
\def\csupervisor#1{\def\@csupervisor{#1}}\def\@csupervisor{}
\def\cdate#1{\def\@cdate{#1}}\def\@cdate{}
\def\etitle#1{\def\@etitle{#1}}\def\@etitle{}


\newcommand{\ecnumcc}[1]{\multicolumn{1}{c}{\underline{\makebox[10em][c]{#1}}}}
\newcommand{\ecnumce}[1]{\multicolumn{1}{c}{\underline{\makebox[15em][l]{#1}}}}

\def\makecover{
  \begin{titlepage}\STSong  %%%%% ===== 中文封面
  \phantomsection\pdfbookmark[0]{封面}{ccover}
  \linespread{1.1}\zihao{4}\ziju{0.05}
  \noindent{\!{\bfseries\@graduateyear}\,届本科生学士学位论文}
  \hfill 学校代码：{\bfseries\underline{\makebox[6em][l]{\,10269}}}

  \begin{center}
    \includegraphics[width=0.73\textwidth]{ecnu_logo}

    \medskip{\linespread{1.0}\selectfont
    \begin{varwidth}[t]{\linewidth}\linespread{1.2}\zihao{1} \@ctitle\end{varwidth}\bigskip

    \begin{varwidth}[t]{\linewidth}\linespread{1.2}\zihao{1} \@etitle \linebreak\end{varwidth}}

    \zihao{4}
    \renewcommand{\arraystretch}{1.5}
    \begin{tabular}{p{0cm}p{4.5em}@{\extracolsep{0.5ex}}cc}
     ~ & 姓 \hfill 名：& & \ecnumcc{\@cauthor}\\
     ~ & 学 \hfill 号：& & \ecnumcc{\@studentid}\\
     ~ & 学 \hfill 院：& & \ecnumcc{\@caffil } \\
     ~ & 专 \hfill 业：& & \ecnumcc{\@cmajor}\\
     ~ & 指\hfill 导\hfill 教\hfill 师：& & \ecnumcc{\@csupervisor}  \\
     ~ & 职 \hfill 称：& & \ecnumcc{\@academictitle}
    \end{tabular}

    \vfill\@cdate
  \end{center}
\end{titlepage}
}

%%%%% baselineskip
\linespread{1.5}

import PySimpleGUI as psg
psg.set_options(font=("Arial Bold",10))
l=psg.Text("Enter Name")
l1=psg.Text("Address for Correspondence")
l2=psg.Text("Permanent Address")
t=psg.Input("", key='-NM-')
a11=psg.Input(key='-a11-')
a12=psg.Input(key='-a12-')
a13=psg.Input(key='-a13-')
col1=[[l1],[a11], [a12], [a13]]
a21=psg.Input(key='-a21-')
a22=psg.Input(key='-a22-')
a23=psg.Input(key='-a23-')
col2=[[l2],[a21], [a22], [a23]]
layout=[[l,t],[psg.Column(col1), psg.Column(col2)], [psg.OK(), psg.Cancel()]]
window = psg.Window('Column Example', layout, size=(800,480))

#   window = sg.Window('Main Window',layout,location=(5000,5000),
#         background_color=sg.theme_background_color(),
#         size=(cont['scr_width'],
#         cont['scr_height']),
#         element_justification='c', 
#         titlebar_background_color = 'blue',
#         titlebar_text_color = 'blue', 
#         keep_on_top=False, finalize=True)     



while True:
   event, values = window.read()
   print (event, values)
   if event in (psg.WIN_CLOSED, 'Exit'):
      break
window.close()
import os
import re
import sys
import glob
import shutil
import nbformat as nbf
from nbformat.v4 import reads, writes, new_markdown_cell, new_code_cell, new_notebook
from nbconvert.exporters.notebook import NotebookExporter
import codecs


def split_code(code):
    '''
    Helper function to extract the docstring lines, the `from __future__`
    imports, and the rest of the code. Also removes shebang lines and encoding
    declarations
    '''
    in_multiline_comment = False
    header_parsed = False
    future_imports = []
    docstring = []
    other_code = []
    for line in code.split('\n'):
        line = line.rstrip()
        if len(line) == 0 and not in_multiline_comment:
            continue
        if re.match(r'^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)', line) is not None:
            continue
        if line.startswith('#!'):
            continue
        if header_parsed:  # past the initial lines with docstring/imports
            other_code.append(line)
        elif in_multiline_comment:
            if line.endswith("'''") or line.endswith('"""'):
                docstring.append(line[:-3])
                in_multiline_comment = False
            else:
                docstring.append(line)
        else:
            if line.startswith('from __future__ import'):
                future_imports.append(line)
            elif line.startswith("'''") or line.startswith('"""'):
                if (line.endswith("'''") or line.endswith('"""')) and len(line) >= 6:
                    # Triple quoted single line docstring
                    docstring.append(line[3:-3])
                else:
                    in_multiline_comment = True
                    docstring.append(line[3:])
            else:
                # Neither `from __future__` import nor docstring --> the rest
                # is the main code of the example
                other_code.append(line)
                header_parsed = True
    if len(future_imports):
        # force an empty line
        future_imports.append('')
    return '\n'.join(future_imports), '\n'.join(docstring), '\n'.join(other_code)

all_tutorials = []
all_examples = []

###################### GENERATE TUTORIAL NOTEBOOKS ############################
note = '''
<div class="clearfix" style="padding: 10px; padding-left: 0px">
<a href="http://briansimulator.org/"><img src="http://briansimulator.org/WordPress/wp-content/ata-images/brian1.png" alt="The Brian spiking neural network simulator" title="The Brian spiking neural network simulator" width="200px" style="display: inline-block; margin-top: 5px;"></a>
<a href="http://mybinder.org/"><img src="https://raw.githubusercontent.com/jupyterhub/binderhub/master/binderhub/static/logo.svg" alt="binder logo" title="binder" width="375px" class="pull-right" style="display: inline-block; margin: 0px;"></a>
</div>

### Quickstart
To run the code below:

1. Click on the cell to select it.
2. Press `SHIFT+ENTER` on your keyboard or press the play button
   (<button class='fa fa-play icon-play btn btn-xs btn-default'></button>) in the toolbar above.

Feel free to create new cells using the plus button
(<button class='fa fa-plus icon-plus btn btn-xs btn-default'></button>), or pressing `SHIFT+ENTER` while this cell
is selected.
<div class="alert alert-block alert-warning" role="alert" style="margin: 10px">
<p><b>WARNING</b></p>
<p>Don't rely on this server for anything you want to last - your session will be
deleted after a short period of inactivity.</p>
</div>

This notebook is running on [mybinder.org](http://mybinder.org) created by the
[Freeman lab](https://www.janelia.org/lab/freeman-lab).
'''
if not os.path.exists('tutorials'):
    os.mkdir('tutorials')
for notebook in sorted(glob.glob('_tutorials/*.ipynb')):
    with open(notebook, 'r') as f:
        content = reads(f.read())
    title = content.cells[0]['source'].split('\n')[0].strip('# ')
    all_tutorials.append((title, notebook[1:].replace('\\', '/')))

    # Insert a note about Jupyter notebooks at the top with a download link
    content.cells.insert(1, new_markdown_cell(note))
    (path, filename) = os.path.split(notebook)

    with open('tutorials/' + filename, 'w') as f:
        nbf.write(content, f)

shutil.rmtree('_tutorials')


###################### GENERATE EXAMPLES NOTEBOOKS ############################

magic = '''%matplotlib notebook\n'''
if not os.path.exists('examples'):
    os.mkdir('examples')
for root, subfolders, files in os.walk('_examples'):
    for file in sorted(files):
        if not os.path.exists(root[1:]):
            os.mkdir(root[1:])
        example = os.path.join(root, file)
        # Copy all files over
        shutil.copy(example, root[1:])

        if file.endswith('.py'):
            # Convert Python files to Jupyter notebooks
            all_examples.append((root[10:].replace('\\', '/'), file))
            with open(example, 'r') as f:
                code = f.read()

            future_imports, docstring, code = split_code(code)

            base, ext = os.path.splitext(os.path.split(example)[-1])

            # Create blank notebook
            content = new_notebook()
            content['cells'] = [new_markdown_cell(note)]
            if len(docstring):
                content['cells'].append(new_markdown_cell(docstring))
            content['cells'].append(new_code_cell(future_imports + magic + code))

            # Add kernel specification
            content['metadata']['kernelspec'] = {"display_name": "Python 3",
                                                 "language": "python",
                                                 "name": "python3"}
            
            exporter = NotebookExporter()
            output, _ = exporter.from_notebook_node(content)
            codecs.open(''.join([root[1:], '/', base, '.ipynb']), 'w',
                        encoding='utf-8').write(output)

shutil.rmtree('_examples')

###################### GENERATE INDEX NOTEBOOK ################################

all_tutorials.sort(key=lambda notebook: notebook[1])  # Sort by filename
tutorials_index = ''
for title, fname in all_tutorials:
    tutorials_index += '* [{title}]({fname})\n'.format(title=title, fname=fname)
examples_index = ''
curroot = ''
for root, fname in all_examples:
    if curroot != root:
        examples_index += '\n'+'#'*(root.count('/')+3)+' '+root+'\n\n'
        curroot = root
    if root:
        fullfname = 'examples/'+root+'/'+fname[:-3]+'.ipynb'
    else:
        fullfname = 'examples/'+fname[:-3]+'.ipynb'
    examples_index += '* [{name}]({fullfname})\n'.format(name=fname[:-3], fullfname=fullfname)

with open('index_template.ipynb', 'r') as f:
    indexnb = reads(f.read())

for cell in indexnb['cells']:
    if 'INSERT_TUTORIALS_HERE' in cell['source']:
        cell['source'] = tutorials_index
    if 'INSERT_EXAMPLES_HERE' in cell['source']:
        cell['source'] = examples_index

with open('index.ipynb', 'w') as f:
    nbf.write(indexnb, f)

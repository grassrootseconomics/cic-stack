docs:
	mkdir -p doc/texinfo/html
	makeinfo doc/texinfo/index.texi --html -o doc/texinfo/html/

markdown: doc
	pandoc -f html -t markdown --standalone doc/texinfo/html/liveness.html -o README.md


.PHONY dist:
	python setup.py sdist

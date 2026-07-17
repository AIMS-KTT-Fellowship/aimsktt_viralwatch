#!/bin/bash


FILE="data/raw/who_pdfs/outbreak_report.pdf"


if [ -f "$FILE" ]
then

echo "File exists"

SIZE=$(du -h "$FILE")

echo "File size:"
echo "$SIZE"


echo "SHA256 checksum:"

sha256sum "$FILE"


else

echo "File missing"

exit 1

fi
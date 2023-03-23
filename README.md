# S3 Upload Image Metadata Extractor using lambda functions

This is a lambda function example on how to extract metadata from uploaded UAV images (RGB or spectral) to an S3 bucket. It checks if the file has the desired metadata and updates a database, while also copying files with metadata to another bucket (bucket_out) for later processing.

This example (`lambda_function.py`) extracts metadata from image files in an S3 bucket, updates a database with the filenames, latitude, and longitude, and copies the files (that sucessfully extracted the desired metadata) to another S3 bucket. This example uses the ExifRead library to extract GPS coordinates from the metadata of the image files. You can modify the code to extract other metadata information you desire.

This was tested sucessfully using DJI and MicaSense sensors from UAV images.

## Dependencies and runtime

* Using Runtime Python 3.7

This Lambda function requires the following dependencies:

`exifread`: A Python library for reading EXIF metadata from image files.
`boto3`: The AWS SDK for Python. It should be already included in AWS lambda functions, no need to create a layer.

## How to Create the Lambda Function

Create an AWS Lambda function with the following settings:

* Runtime: Python 3.7

Update the lines: `bucket_out = '<output-bucket-name>'` to your output bucket name.

Copy the code in `lambda_function.py` to the lambda function or Upload the `lambda_function.py` file to your Lambda function.

Lambda Execution role: Choose an existing role with permission to read from and write to your S3 buckets. (S3FullAccess will work, but make sure you only give the correct permissions you need)

Add the exifread dependencies to your Lambda function as a layer.

Add trigger event to your lambda function (example: "All object create events"), add prefix or suffixes if applicable.

## Usage

After deploying the Lambda function, any image files uploaded to the input S3 bucket will trigger the function to extract the GPS metadata and save it to a text file in the output S3 bucket.

## Notes

Depending on the size of your images, you might require more timeout or allocated memory for your lambda. Make sure to setup the correct timeout and memory allocated to your function in Lambda > Functions > YourLambda > Configuration > General configuration. 

## How to create the exifread-layer for your runtime version:

1. Create a virtual environment with Python 3.7 or the python version of your lambda runtime (optional): `conda create --name <env-name> python=3.7` or `virtualenv <env-name> --python=python3.7`
2. Activate the virtual environment (optional): `conda activate <env-name>` or `source <env-name>/bin/activate`
3. Create a new directory and navigate to it: `mkdir exifread-layer` and then `cd exifread-layer` 
4. Create a new python directory: `mkdir python`
5. Install the exifread library inside the python directory: `pip install exifread -t python`
6. Create an empty file named `__init__.py` inside the python directory: `touch python/__init__.py`
7. Create a new ZIP archive that contains the python directory: `zip -r exifread-layer.zip python`
8. Upload the `exifread-layer.zip` archive to an S3 bucket in your AWS account (optional).
9. Create a new Lambda layer in your AWS account and upload the `exifread-layer.zip` archive or use the uploaded version to S3.
10. Attach the layer to your Lambda function.


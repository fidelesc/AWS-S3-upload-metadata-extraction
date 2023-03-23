import boto3
import json
import exifread
from io import BytesIO

def extract_coordinates(image_bytes):
    # Create a BytesIO object from the image bytes
    image_file = BytesIO(image_bytes)
    # Open image file for reading (must be in binary mode)
    tags = exifread.process_file(image_file)
    if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
        latitude = tags['GPS GPSLatitude'].values
        longitude = tags['GPS GPSLongitude'].values
        lat_ref = tags['GPS GPSLatitudeRef'].values
        lon_ref = tags['GPS GPSLongitudeRef'].values
        lat = convert_to_degrees(latitude)
        lon = convert_to_degrees(longitude)
        if lat_ref == 'S':
            lat = -lat
        if lon_ref == 'W':
            lon = -lon
        return lat, lon
    return None

def convert_to_degrees(values):
    d = float(values[0].num) / float(values[0].den)
    m = float(values[1].num) / float(values[1].den)
    s = float(values[2].num) / float(values[2].den)
    return d + (m / 60.0) + (s / 3600.0)

s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')

bucket_out = '<output-bucket-name>'

def lambda_handler(event, context):
    # Extract the S3 bucket name and object key from the trigger event
    bucket_in = event['Records'][0]['s3']['bucket']['name']
    s3_object_key = event['Records'][0]['s3']['object']['key']

    # Get the S3 object and extract GPS metadata
    response = s3.get_object(Bucket=bucket_in, Key=s3_object_key)
    image_bytes = response['Body'].read()
    try:
        gps_coordinates = extract_coordinates(image_bytes)
    except Exception as e:
        print(f"Failed to extract coordinates for image {s3_object_key}: {e}")
        return

    # Copy object to output bucket with same key and prefix if GPS metadata is available
    if gps_coordinates is not None:
        copy_source = {'Bucket': bucket_in, 'Key': s3_object_key}
        output_key = s3_object_key
        s3.copy_object(Bucket=bucket_out, Key=output_key, CopySource=copy_source)
        print("Copied file with GPS metadata:", s3_object_key)
    else:
        print("No GPS coordinates found in file:", s3_object_key)

    return {
        'statusCode': 200,
        'body': f'Processed file: {s3_object_key}'
    }


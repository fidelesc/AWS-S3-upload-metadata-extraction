# Import required libraries
import boto3
import exifread
from io import BytesIO
import uuid
import os

# Establish connection with S3, Lambda, and DynamoDB services in AWS
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb', region_name='<your-dynamordb-region>') # Substitute with your region

# Specify the DynamoDB table
dynamo_table = dynamodb.Table('<dynamodb-table-name>') # Substitute with your DynamoDB table name

# Specify the output bucket name
bucket_out = '<output-bucket-name>' # Substitute with your output bucket name

# Function to add a new file and update the corresponding upload
def add_file(item_id, s3_entry_path, metadata, s3_output_path = None):
    # If no output path is provided, the status is 'error'
    if s3_output_path == None:
        status = "error"
    else:
        status = "processed"

    # Add new table entry to DynamoDB with item details and metadata
    dynamo_table.put_item(
        Item={
            'itemId': item_id,
            'entryPath': s3_entry_path,
            'outputPath': s3_output_path,
            'status': status,
            'latitude': metadata[0],
            'longitude': metadata[1],
            'size': str(metadata[2]),
            'pixels': metadata[3]
        }
    )

# Function to compute file size in MB
def get_file_size(image_bytes):
    return len(image_bytes) / (1024 * 1024)

# Function to extract EXIF metadata from image
def extract_metadata(image_bytes):
    # Use BytesIO object to process image file in binary mode
    image_file = BytesIO(image_bytes)
    tags = exifread.process_file(image_file)
    
    file_size_mb = get_file_size(image_bytes)
    lat = None
    lon = None
    width = None
    height = None
    
    if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags: #for DJI RGB, Micasense cameras
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
    if 'EXIF ExifImageWidth' in tags and 'EXIF ExifImageLength' in tags: #for DJI RGB images
    # Get image size (width, height) from EXIF data
        width = tags['EXIF ExifImageWidth'].values[0]
        height = tags['EXIF ExifImageLength'].values[0]
    elif 'Image ImageWidth' in tags and 'Image ImageLength' in tags: #for Micasense cameras
        width = tags['Image ImageWidth'].values[0]
        height = tags['Image ImageLength'].values[0]
        
    metadata = [str(lat), str(lon), float(round(file_size_mb, 2)), int(width*height)]
        
    return metadata

# Function to convert GPS coordinates to decimal degrees
def convert_to_degrees(values):
    # Extract the degrees, minutes, and seconds from the GPS coordinate
    # Convert to decimal degrees
    d = float(values[0].num) / float(values[0].den)
    m = float(values[1].num) / float(values[1].den)
    s = float(values[2].num) / float(values[2].den)
    return d + (m / 60.0) + (s / 3600.0)

def lambda_handler(event, context):
    # Create a unique ID for the item
    item_id = str(uuid.uuid4())
    
    # Extract the S3 bucket name and object key from the triggered event
    bucket_in = event['Records'][0]['s3']['bucket']['name']
    s3_object_key = event['Records'][0]['s3']['object']['key']
    
    try:
        # Extract the file extension
        file_ext = os.path.splitext(s3_object_key)[1]
    except:
        # If no extension detected, you can use .txt or .log file to output the error
        file_ext = ".txt"
        
    entryPath = bucket_in+":"+s3_object_key

    # Get the S3 object and extract GPS metadata
    response = s3.get_object(Bucket=bucket_in, Key=s3_object_key)
    image_bytes = response['Body'].read()
    
    try:
        metadata  = extract_metadata(image_bytes)
        print(f"Image size: {metadata[3]} pixels")
        print(f"File size: {metadata[2]} MB")
        print(f"Latitude: {metadata[0]} , Longitude: {metadata[1]}")
        
        status = True
        
    except Exception as e:
        print(f"Failed to extract metadata for image {s3_object_key}: {e}")
        status = False
    
    # Copy object to output bucket with same key and prefix if GPS metadata is available
    if status:
        copy_source = {'Bucket': bucket_in, 'Key': s3_object_key}
        
        output_key = item_id+file_ext
        outputPath = bucket_out+":"+output_key
        
        s3.copy_object(Bucket=bucket_out, Key=output_key, CopySource=copy_source)
        print("Copied file with metadata:", output_key)

        ## Send metadata to database
        add_file(item_id, entryPath, metadata, s3_output_path=outputPath)

    else:
        add_file(item_id, entryPath, metadata)
        print("No metadata found in file:", s3_object_key)
        

    return {
        'statusCode': 200,
        'body': f'Processed file: {s3_object_key}'
    }

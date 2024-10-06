# src.animation_COPERNICUS_S5P_NRTI_L3_HCHO.py
import ee
import os
import geemap
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

# Get the project key from the environment variables
gee_project = os.getenv('GEE_PROJECT')

# Authentication and initialization of Google Earth Engine
ee.Authenticate()
ee.Initialize(project=gee_project)

# Define the area of interest: Latin America from Brazil downward
region = ee.Geometry.Polygon([
    [
        [-92, 13],    # Northwest corner (Mexico-Guatemala border)
        [-92, -56],   # Southwest corner (southern tip of South America)
        [-30, -56],   # Southeast corner
        [-30, 13]     # Northeast corner
    ]
])

# Define the date range for the animation
startDate = '2024-09-01'
endDate = '2024-10-04'

# Load the image collection for HCHO
collection = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_HCHO') \
    .select('tropospheric_HCHO_column_number_density') \
    .filterDate(startDate, endDate) \
    .filterBounds(region)

# Correctly calculate the number of composites
daysPerComposite = 4
start = ee.Date(startDate)
end = ee.Date(endDate)

# Get the total number of days as a Python number
nDays = end.difference(start, 'day').getInfo()
nComposites = int((nDays + daysPerComposite - 1) // daysPerComposite)

# Create composites
def create_composite(i):
    i = ee.Number(i)
    compositeStart = start.advance(i.multiply(daysPerComposite), 'day')
    compositeEnd = compositeStart.advance(daysPerComposite, 'day')
    composite = collection.filterDate(compositeStart, compositeEnd).mean() \
        .set('system:time_start', compositeStart.millis()) \
        .set('label', compositeStart.format('YYYY-MM-dd')
             .cat(' to ')
             .cat(compositeEnd.advance(ee.Number(-1), 'day').format('YYYY-MM-dd')))
    return composite

composites = ee.ImageCollection(
    ee.List.sequence(0, nComposites - 1).map(create_composite)
)

# Filter out empty composites (optional but recommended)
composites = composites.filter(ee.Filter.listContains('system:band_names', 'tropospheric_HCHO_column_number_density'))

# Visualization parameters for HCHO
hchoVizParams = {
    'min': 0.0,
    'max': 0.0003,
    'palette': ['black', 'blue', 'purple', 'cyan', 'green', 'yellow', 'red']
}

# Create a visualized image collection
def visualize_image(image):
    image_vis = image.visualize(**hchoVizParams).set({
        'system:time_start': image.get('system:time_start'),
        'label': image.get('label')
    })
    return image_vis

visCollection = composites.map(visualize_image)

# --- Add the borders of the countries ---

# Load country boundaries
countries = ee.FeatureCollection('USDOS/LSIB_SIMPLE/2017')

# Filter the country boundaries to the region
countriesInRegion = countries.filterBounds(region)

# Create an image of the borders
borders = ee.Image().byte().paint(
    featureCollection=countriesInRegion,
    color=1,
    width=1
)

# Style the borders
bordersImage = borders.visualize(
    palette=['white'],
    forceRgbOutput=True
)

# Function to add borders to images
def add_borders(image):
    image_with_borders = ee.ImageCollection([image, bordersImage]).mosaic()
    return image_with_borders.copyProperties(image, image.propertyNames())

# Apply the add_borders function to each image
visCollectionWithBorders = visCollection.map(add_borders)

# Function to add text labels to images
def add_text(image):
    # Note: Adding dynamic text labels directly in Earth Engine Python API is limited
    # geemap provides functions to annotate images, but they cannot be used directly in a map over an ImageCollection
    # As a workaround, we'll proceed without adding text labels in this script
    return image

# Apply the add_text function to each image (currently does nothing)
annotatedVisCollection = visCollectionWithBorders.map(add_text)

# GIF visualization parameters
gif_params = {
    'region': region,
    'dimensions': 800,
    'framesPerSecond': 1,
    'crs': 'EPSG:3857',
}

# Generate and save the annotated animated GIF
gif_file = 'HCHO_Animation_LatinAmerica.gif'
geemap.ee_export_image_collection_to_gif(
    collection=annotatedVisCollection,
    out_gif=gif_file,
    fps=1,
    region=region,
    dimensions=800
)
print(f'Animated GIF has been saved to {gif_file}')

# Display the GIF in a Jupyter notebook (optional)
# from IPython.display import Image
# Image(gif_file)

# Export the animation as a video to Google Drive
task_config = {
    'collection': annotatedVisCollection,
    'description': 'HCHO_Animation_LatinAmerica',
    'dimensions': 720,
    'framesPerSecond': 1,
    'region': region,
}

task = ee.batch.Export.video.toDrive(**task_config)
task.start()
print('Exporting video to Google Drive. Please check the Tasks tab in the Code Editor.')
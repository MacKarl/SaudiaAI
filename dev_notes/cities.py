def markdown_to_csv(markdown_file, csv_file):
    with open(markdown_file, 'r') as md:
        lines = md.readlines()
    
    # Let's skip the markdown table separators. We assume they're always in the second line.
    lines = [line.strip() for line in lines if not line.startswith('|-')]
    
    # Now, the magic - replace markdown pipe separators with commas and trim spaces.
    csv_lines = [line.replace('|', ',').strip(',') for line in lines]
    
    # Writing our beautifully transformed data to a CSV, because everyone loves CSVs.
    with open(csv_file, 'w') as csv:
        csv.write('\n'.join(csv_lines))
    
    print("Transformation complete. Check your CSV, it's probably sparkling.")

# Call the function with the path to your markdown file and the desired output csv file
markdown_to_csv('prop.md', 'properties.csv')

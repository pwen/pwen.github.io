require 'json'
require 'yaml'
require 'date'

# Generate tags data JSON
tags_data = {}

# Read all posts
Dir.glob('_posts/*.md').each do |post_file|
  content = File.read(post_file)
  
  # Extract front matter
  if content =~ /\A(---\s*\n.*?\n?)^(---\s*$\n?)/m
    front_matter = YAML.safe_load($1, permitted_classes: [Date, Time], aliases: true)
    body = $'
    
    # Use custom excerpt from front matter, or fallback to body
    excerpt_text = front_matter['excerpt'] || body.strip[0..1200]
    
    if front_matter['tags']
      tags = front_matter['tags']
      date = front_matter['date']
      
      # Extract title slug from filename (remove date prefix)
      filename = File.basename(post_file, '.md')
      title_slug = filename.sub(/^\d{4}-\d{2}-\d{2}-/, '')
      
      # Build post data
      post_data = {
        'title' => front_matter['title'],
        'url' => "/posts/#{date.year}-#{sprintf('%02d', date.month)}-#{sprintf('%02d', date.day)}-#{title_slug}/",
        'date' => date.strftime('%m/%d/%y'),
        'excerpt' => excerpt_text,
        'image' => front_matter['image']
      }
      
      # Add to each tag
      tags.each do |tag|
        tags_data[tag] ||= []
        tags_data[tag] << post_data
      end
    end
  end
end

# Sort posts by date (newest first)
tags_data.each do |tag, posts|
  tags_data[tag] = posts.sort_by { |p| p['url'] }.reverse
end

# Write JSON file
File.open('assets/tags-data.json', 'w') do |f|
  f.write(JSON.pretty_generate(tags_data))
end

puts "Generated assets/tags-data.json with #{tags_data.keys.length} tags"

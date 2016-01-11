desc "Build graphite-beacon docker"
task :build do
  sh "docker build -t graphite-beacon . "
end

desc "Run demo docker container"
task :run => :build do
  sh "docker run -v $(pwd)/examples/example-config.json:/config.json graphite-beacon"
end
